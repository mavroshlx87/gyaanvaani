"""Stage 1: Generate 100+ mythology stories using local Ollama + Qwen3:8b."""

import sys
import os
import json
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import ollama
from shared.store import save_story, count_by_status, get_all_titles
from shared.ollama_utils import load_model, unload_all
from shared.logger import setup_logger

logger = setup_logger("stage1")

MODEL = "qwen3:8b"
STORIES_PER_CALL = 5    # Keep small to avoid context truncation
BATCHES_PER_SOURCE = 2  # 2 x 5 = 10 stories per source

SYSTEM_PROMPT = """You are a master children's storyteller specializing in Indian mythology.

Generate exactly {count} unique stories from the specified source text.

RULES:
- Target age: 4-10 years old
- Each story: 800-1000 words
- Structure: Setup → Conflict → Resolution
- End with explicit, simple moral lesson
- Use vivid visual descriptions (colors, scenery, character appearance)
- NO violence, gore, adult themes, scary content
- Characters should feel relatable to modern children
- Each story must be about a DIFFERENT episode/event — no repeats

OUTPUT: Valid JSON array only, no markdown fences. Schema:
[{{
  "title": "Story Title",
  "source": "Source Text Name",
  "characters": ["Character1", "Character2"],
  "full_story": "Long ago... (800-1000 words)",
  "moral": "One sentence moral lesson.",
  "tags": ["tag1", "tag2"]
}}]"""

# Source sections to generate stories from
SOURCES = [
    ("Ramayana - Bala Kanda", "childhood of Rama, Sita Swayamvar, breaking Shiva's bow"),
    ("Ramayana - Ayodhya Kanda", "Rama's exile, Bharata's devotion, Shabari's berries"),
    ("Ramayana - Aranya Kanda", "forest adventures, Jatayu's sacrifice, golden deer"),
    ("Ramayana - Sundara Kanda", "Hanuman's journey to Lanka, finding Sita"),
    ("Ramayana - Yuddha Kanda", "building the bridge, Vibhishana's righteousness"),
    ("Mahabharata - childhood stories", "Arjuna's focus, Bhima's strength, Drona's test"),
    ("Mahabharata - moral dilemmas", "Yudhishthira's truthfulness, Karna's generosity"),
    ("Bhagavata Purana - Krishna's childhood", "butter thief, Govardhan hill, Kaliya serpent"),
    ("Panchatantra - Book 1", "animal fables about friendship and trust"),
    ("Panchatantra - Book 2-3", "animal fables about wisdom and cleverness"),
    ("Hitopadesha", "tales of wise counsel and good friendship"),
    ("Jataka Tales", "Buddhist animal fables from ancient India"),
]


def extract_json(text: str) -> list:
    """Extract JSON array from LLM response, handling markdown fences."""
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r'^```(?:json)?\s*\n?', '', text)
        text = re.sub(r'\n?```\s*$', '', text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r'\[.*\]', text, re.DOTALL)
        if match:
            return json.loads(match.group())
        raise


def generate_stories(source_name: str, source_desc: str, existing_slugs: set,
                     count: int = STORIES_PER_CALL, batch: int = 1):
    """Generate stories from a single source, avoiding duplicates."""
    logger.info(f"Generating {count} stories from: {source_name} (batch {batch})")

    # Build avoid list from existing titles
    avoid_list = ""
    if existing_slugs:
        sample = list(existing_slugs)[:30]
        # Convert slugs back to readable titles for the LLM
        readable = [s.replace("_", " ").title() for s in sample]
        avoid_list = (
            "\n\nDO NOT generate stories with these titles (already exist):\n"
            + "\n".join(f"- {t}" for t in readable)
        )

    response = ollama.chat(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT.format(count=count)},
            {"role": "user", "content": (
                f"Generate {count} unique children's stories from: {source_name}\n"
                f"Key themes/episodes to cover: {source_desc}\n"
                f"Batch {batch} — pick DIFFERENT episodes than previous batches."
                f"{avoid_list}\n\n"
                f"Output valid JSON array only."
            )}
        ],
        options={"temperature": 0.8, "num_ctx": 16384}
    )

    raw = response["message"]["content"]
    try:
        stories = extract_json(raw)
    except (json.JSONDecodeError, Exception) as e:
        logger.error(f"Failed to parse JSON for {source_name}: {e}")
        logger.error(f"Raw output (first 500 chars): {raw[:500]}")
        return 0, existing_slugs

    inserted = 0
    for story in stories:
        if not all(k in story for k in ["title", "full_story", "moral"]):
            logger.warning(f"Skipping story with missing fields: {story.get('title', 'unknown')}")
            continue

        # Dedup: slugify title and check against existing
        slug = re.sub(r'[^a-z0-9]+', '_', story["title"].lower().strip()).strip('_')[:60]
        if slug in existing_slugs:
            logger.warning(f"  ✗ Duplicate skipped: {story['title']}")
            continue

        story["source"] = story.get("source", source_name)
        filename = save_story(story)
        existing_slugs.add(slug)
        inserted += 1
        logger.info(f"  ✓ {filename}")

    return inserted, existing_slugs


def main():
    logger.info("=== Stage 1: Story Generation ===")
    logger.info(f"Config: {STORIES_PER_CALL} stories/call x {BATCHES_PER_SOURCE} batches x {len(SOURCES)} sources")

    # Load existing slugs for dedup
    existing_slugs = get_all_titles()
    if existing_slugs:
        logger.info(f"Found {len(existing_slugs)} existing stories — will skip duplicates")

    # Load model once
    load_model(MODEL)

    total = 0
    for source_name, source_desc in SOURCES:
        source_count = 0
        for batch in range(1, BATCHES_PER_SOURCE + 1):
            count, existing_slugs = generate_stories(
                source_name, source_desc, existing_slugs,
                count=STORIES_PER_CALL, batch=batch
            )
            source_count += count
        total += source_count
        logger.info(f"  → {source_count} stories from {source_name}")

    # Free RAM
    unload_all()

    pending = count_by_status("pending")
    logger.info(f"=== Done. Generated {total} new stories. Total pending: {pending} ===")


if __name__ == "__main__":
    main()
