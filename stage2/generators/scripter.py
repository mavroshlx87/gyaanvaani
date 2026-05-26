"""Scene scripter: breaks a story into 15-20 visual scenes with image prompts.

Enhanced with Character Lookup Engine (Plan A) — injects consistent character
appearances from data/characters/ database into every scene prompt.
"""

import json
import re
import ollama
from shared.logger import setup_logger
from shared.character_store import get_store
from shared.character_generator import ensure_characters_exist
from config.settings import STORY_MODEL

logger = setup_logger("scripter")

SCENE_PROMPT = """Break this children's story into exactly 18 visual scenes for an animated storybook video.

STORY:
{story}

{character_descriptions}

For each scene output JSON array:
[{{
  "scene_number": 1,
  "narration_text": "what the narrator says for this scene",
  "image_prompt": "3D Pixar style, [detailed visual description], vibrant colors, soft lighting, child-friendly, 16:9",
  "duration_seconds": 25,
  "camera_motion": "slow_zoom_in"
}}]

RULES:
- 18 scenes, 20-30 seconds each (total ~7-8 min)
- image_prompt MUST start with "3D Pixar style"
- Use the CHARACTER APPEARANCES above to describe each character EXACTLY and CONSISTENTLY in every image_prompt where they appear
- camera_motion: one of slow_zoom_in, slow_zoom_out, pan_left, pan_right
- Last scene must show the moral lesson visually
- Output valid JSON array only, no markdown"""


def _build_character_block(story: dict) -> str:
    """Build character appearance descriptions from the character database.

    Looks up each character mentioned in the story and returns a formatted
    block of their physical descriptions for injection into the scene prompt.

    If a character is NOT in the database, auto-generates their profile first.
    If a character IS already in the database, uses the existing one (no duplicates).
    """
    characters = story.get("characters", [])
    if not characters:
        return ""

    store = get_store()

    # AUTO-GENERATE: create profiles for any characters not yet in the database
    # Characters already in the store are skipped (no duplicates)
    newly_generated = ensure_characters_exist(characters, story, store)

    # Determine timeline hint from story source/context
    source = story.get("source", "").lower()
    timeline_hint = None
    if "exile" in source or "aranya" in source or "forest" in source:
        timeline_hint = "exile forest"
    elif "war" in source or "yuddha" in source or "kurukshetra" in source:
        timeline_hint = "war battle"
    elif "childhood" in source or "bala" in source or "youth" in source:
        timeline_hint = "youth child"
    elif "king" in source or "rajya" in source:
        timeline_hint = "king queen court"

    desc_block = store.get_scene_character_descriptions(characters, timeline_hint)

    if desc_block:
        existing_count = len(characters) - len(newly_generated)
        logger.info(
            f"  Injected {len(characters)} character descriptions "
            f"({existing_count} from database, {len(newly_generated)} auto-generated)"
        )
        return desc_block
    else:
        # Fall back: log which characters were not found
        for name in characters:
            if not store.has_character(name):
                logger.debug(f"  Character not in database: {name}")
        return ""


def generate_scenes(story: dict) -> list:
    """Generate scene breakdown for a story.

    Enhanced: injects character appearance descriptions from the character
    database for visual consistency across all videos.
    """
    logger.info(f"  Scripting scenes for: {story['title']}")

    # Build character description block from database
    char_block = _build_character_block(story)

    resp = ollama.chat(model=STORY_MODEL, messages=[{
        "role": "user",
        "content": SCENE_PROMPT.format(
            story=story["full_story"][:3000],
            character_descriptions=char_block
        )
    }], options={"temperature": 0.7, "num_ctx": 8192})

    raw = resp["message"]["content"]
    # Clean thinking tags
    raw = re.sub(r'<think>.*?</think>', '', raw, flags=re.DOTALL).strip()
    # Remove markdown fences
    if raw.startswith("```"):
        raw = re.sub(r'^```(?:json)?\s*\n?', '', raw)
        raw = re.sub(r'\n?```\s*$', '', raw)

    try:
        scenes = json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r'\[.*\]', raw, re.DOTALL)
        if match:
            scenes = json.loads(match.group())
        else:
            raise ValueError(f"Could not parse scenes JSON: {raw[:300]}")

    logger.info(f"  Generated {len(scenes)} scenes")
    return scenes
