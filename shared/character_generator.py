"""Auto-generate character profiles for unknown characters using Ollama.

When a story introduces a character not yet in the database, this module
generates their profile JSON using the LLM, saves it to
data/characters/auto_generated/, and hot-registers it in the CharacterStore.

Usage:
    from shared.character_generator import ensure_characters_exist
    ensure_characters_exist(["Rama", "NewChar"], story_dict, store)
    # "Rama" → already exists, skipped
    # "NewChar" → generated, saved, registered
"""

import json
import os
import re
import ollama
from typing import Optional
from shared.logger import setup_logger
from config.settings import STORY_MODEL

logger = setup_logger("character_generator")

# Where auto-generated character files are saved
AUTO_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "characters", "auto_generated"
)

# Counter file to track AUTO_NNN IDs
COUNTER_FILE = os.path.join(AUTO_DIR, "_counter.json")

# Words that are NOT real characters — skip these
SKIP_WORDS = {
    "narrator", "villagers", "village", "people", "crowd", "soldiers",
    "army", "citizens", "gods", "demons", "animals", "birds", "fish",
    "servants", "guards", "children", "monks", "sages", "warriors",
    "townspeople", "farmers", "merchants", "ministers", "attendants",
    "courtiers", "subjects", "elders", "women", "men", "devas",
    "asuras", "rakshasas", "gandharvas", "apsaras", "yakshas",
}

# The prompt sent to the LLM to generate a character profile
GENERATE_PROMPT = """You are an expert on Indian mythology (Ramayana, Mahabharata, Puranas, Panchatantra, Jataka tales).

Generate a detailed character profile for: **{character_name}**

Context from the story where this character appears:
- Story title: {story_title}
- Story source: {story_source}
- Other characters in the story: {other_characters}
- Brief excerpt: {story_excerpt}

Output a single valid JSON object following this EXACT structure (no markdown fences, no extra text):
{{
    "{char_key}": {{
        "metadata": {{
            "character_id": "{char_id}",
            "name": "{character_name}",
            "aliases": ["list of alternative names, epithets, titles for this character"],
            "epic": "Ramayana or Mahabharata or Panchatantra or Jataka or Puranas",
            "primary_role": "brief role description",
            "gender": "Male or Female",
            "ethnicity_cultural_context": "dynasty, kingdom, cultural background",
            "family_relations": {{
                "father": "name or null",
                "mother": "name or null",
                "spouse": "name or null",
                "siblings": [],
                "children": [],
                "guru": "name or null"
            }},
            "divine_origin": "divine parentage or null",
            "tags": ["searchable", "tags"]
        }},
        "timelines": [
            {{
                "timeline_stage": "Primary / Most Common Depiction",
                "age_approximation": 30,
                "context_description": "Detailed description of the character in their most commonly depicted form",
                "physical_appearance": {{
                    "skin_tone": "detailed skin color description",
                    "height": "height description",
                    "build": "body build description",
                    "facial_features": "detailed face description",
                    "hair": "hair description",
                    "distinguishing_marks": "unique features, scars, marks, auras"
                }},
                "wardrobe_and_adornments": {{
                    "clothing": "detailed outfit description with colors and materials",
                    "jewelry": "crown, armlets, necklaces with materials",
                    "weapons_carried": "specific weapons with names if divine"
                }},
                "audio_and_voice_characteristics": {{
                    "tone": "emotional quality of voice",
                    "pitch": "bass/baritone/tenor/alto/soprano",
                    "speech_style": "how they speak, cadence, vocabulary",
                    "emotional_baseline": "default emotional state"
                }},
                "cinematic_generation_prompts": {{
                    "visual_prompt": "3D Pixar style, [character name], [age], [skin], [build], [clothing], [setting]. Photorealistic, 8k, vibrant colors, child-friendly.",
                    "audio_prompt": "A [pitch] [gender] voice. [tone]. [speech_style]. Age approximately [age] years."
                }}
            }}
        ]
    }}
}}

RULES:
- Be mythologically accurate — use real information from scriptures
- The visual_prompt MUST start with "3D Pixar style"
- The visual_prompt should be child-friendly (no gore, no scary imagery)
- Include at least 3 aliases (alternative names)
- Output valid JSON only — no markdown fences, no explanations"""


def _get_next_id() -> tuple:
    """Get the next AUTO_NNN ID and increment the counter."""
    os.makedirs(AUTO_DIR, exist_ok=True)

    counter = 1
    if os.path.exists(COUNTER_FILE):
        try:
            with open(COUNTER_FILE, "r") as f:
                data = json.load(f)
                counter = data.get("next_id", 1)
        except (json.JSONDecodeError, Exception):
            counter = 1

    char_id = f"AUTO_{counter:03d}"

    # Save incremented counter
    with open(COUNTER_FILE, "w") as f:
        json.dump({"next_id": counter + 1}, f)

    return char_id, counter


def _slugify(name: str) -> str:
    """Convert a character name to a filename-safe slug."""
    return re.sub(r'[^a-z0-9]+', '_', name.lower().strip()).strip('_')


def _should_skip(name: str) -> bool:
    """Check if a name is a generic word rather than a real character."""
    clean = name.lower().strip()
    if clean in SKIP_WORDS:
        return True
    if len(clean) < 2:
        return True
    # Skip if it's just "the X" or "a X"
    if clean.startswith("the ") or clean.startswith("a "):
        return True
    return False


def generate_character_profile(
    character_name: str,
    story: dict,
    other_characters: list = None
) -> Optional[dict]:
    """Generate a single character profile using Ollama.

    Args:
        character_name: The name of the character to generate
        story: The story dict containing title, source, full_story
        other_characters: Other character names in the story for context

    Returns:
        The generated character data dict, or None if generation fails
    """
    if _should_skip(character_name):
        logger.debug(f"  Skipping generic word: {character_name}")
        return None

    char_id, counter = _get_next_id()
    slug = _slugify(character_name)
    char_key = slug.upper()

    other_chars = [c for c in (other_characters or []) if c != character_name]

    prompt = GENERATE_PROMPT.format(
        character_name=character_name,
        story_title=story.get("title", "Unknown"),
        story_source=story.get("source", "Unknown"),
        other_characters=", ".join(other_chars) if other_chars else "None listed",
        story_excerpt=story.get("full_story", "")[:500],
        char_key=char_key,
        char_id=char_id
    )

    logger.info(f"  🔨 Auto-generating character profile: {character_name} ({char_id})")

    try:
        resp = ollama.chat(
            model=STORY_MODEL,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.6, "num_ctx": 8192}
        )
        raw = resp["message"]["content"]

        # Clean thinking tags and markdown fences
        raw = re.sub(r'<think>.*?</think>', '', raw, flags=re.DOTALL).strip()
        if raw.startswith("```"):
            raw = re.sub(r'^```(?:json)?\s*\n?', '', raw)
            raw = re.sub(r'\n?```\s*$', '', raw)

        # Try to parse the JSON
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            # Try to extract the JSON object
            match = re.search(r'\{.*\}', raw, re.DOTALL)
            if match:
                data = json.loads(match.group())
            else:
                logger.error(f"  ✗ Failed to parse character JSON for {character_name}: {raw[:300]}")
                return None

        # Validate basic structure
        if not isinstance(data, dict) or not data:
            logger.error(f"  ✗ Invalid character data structure for {character_name}")
            return None

        # Get the actual key (LLM might have used a different key)
        actual_key = list(data.keys())[0]
        char_data = data[actual_key]

        if "metadata" not in char_data or "timelines" not in char_data:
            logger.error(f"  ✗ Missing metadata/timelines for {character_name}")
            return None

        # Normalize: ensure character_id and name are correct
        char_data["metadata"]["character_id"] = char_id
        char_data["metadata"]["name"] = character_name

        # Save to file
        filename = f"{char_id}_{slug}.json"
        filepath = os.path.join(AUTO_DIR, filename)
        os.makedirs(AUTO_DIR, exist_ok=True)

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump({actual_key: char_data}, f, indent=4, ensure_ascii=False)

        logger.info(f"  ✓ Generated and saved: {filename}")

        return {
            "filepath": filepath,
            "key": actual_key,
            "name": character_name,
            "aliases": char_data["metadata"].get("aliases", []),
            "data": {actual_key: char_data}
        }

    except Exception as e:
        logger.error(f"  ✗ Error generating character {character_name}: {e}")
        return None


def ensure_characters_exist(
    character_names: list,
    story: dict,
    store
) -> list:
    """Ensure all characters in the list exist in the store.

    For each character:
    1. If already in the store → skip (no duplicate generation)
    2. If a generic word (narrator, villagers, etc.) → skip
    3. Otherwise → generate profile, save, and hot-register in the store

    Args:
        character_names: List of character names from the story
        story: The story dict for context
        store: The CharacterStore instance

    Returns:
        List of character names that were newly generated
    """
    newly_generated = []

    for name in character_names:
        # DEDUP CHECK: skip if character already exists in the database
        if store.has_character(name):
            logger.debug(f"  ✓ Character exists: {name}")
            continue

        # Skip generic/non-character words
        if _should_skip(name):
            continue

        # Generate the profile
        result = generate_character_profile(
            character_name=name,
            story=story,
            other_characters=character_names
        )

        if result:
            # Hot-register in the store so it's immediately available
            store.register_character(
                filepath=result["filepath"],
                key=result["key"],
                name=result["name"],
                aliases=result["aliases"]
            )
            newly_generated.append(name)

    if newly_generated:
        logger.info(
            f"  📚 Auto-generated {len(newly_generated)} new character(s): "
            f"{', '.join(newly_generated)}"
        )

    return newly_generated
