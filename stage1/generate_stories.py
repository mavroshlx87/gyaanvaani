"""Stage 1: Generate 100+ mythology stories using local Ollama + Qwen3:8b."""

import sys
import os
import json
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import ollama
from shared.db import insert_story, count_by_status, init_db
from shared.ollama_utils import load_model, unload_all
from shared.logger import setup_logger

logger = setup_logger("stage1")

MODEL = "qwen3:8b"

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

OUTPUT: Valid JSON array only, no markdown fences. Schema:
[{{
  "title": "Story Title",
  "source": "Source Text Name",
  "characters": ["Character1", "Character2"],
  "full_story": "Long ago... (800-1000 words)",
  "moral": "One sentence moral lesson.",
  "tags": ["tag1", "tag2"]
}}]"""

# Source sections to generate stories from (10 stories each → 100+ total)
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
    # Remove thinking tags if present
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    # Try direct parse
    text = text.strip()
    # Remove markdown code fences if present
    if text.startswith("```"):
        text = re.sub(r'^```(?:json)?\s*\n?', '', text)
        text = re.sub(r'\n?```\s*$', '', text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to find JSON array in the text
        match = re.search(r'\[.*\]', text, re.DOTALL)
        if match:
            return json.loads(match.group())
        raise


def generate_stories(source_name: str, source_desc: str, count: int = 10):
    """Generate stories from a single source."""
    logger.info(f"Generating {count} stories from: {source_name}")

    response = ollama.chat(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT.format(count=count)},
            {"role": "user", "content": (
                f"Generate {count} unique children's stories from: {source_name}\n"
                f"Key themes/episodes to cover: {source_desc}\n"
                f"Output valid JSON array only."
            )}
        ],
        options={"temperature": 0.8, "num_ctx": 8192}
    )

    raw = response["message"]["content"]
    try:
        stories = extract_json(raw)
    except (json.JSONDecodeError, Exception) as e:
        logger.error(f"Failed to parse JSON for {source_name}: {e}")
        logger.error(f"Raw output (first 500 chars): {raw[:500]}")
        return 0

    inserted = 0
    for story in stories:
        # Validate required fields
        if not all(k in story for k in ["title", "full_story", "moral"]):
            logger.warning(f"Skipping story with missing fields: {story.get('title', 'unknown')}")
            continue
        story["source"] = story.get("source", source_name)
        insert_story(story)
        inserted += 1
        logger.info(f"  ✓ {story['title']}")

    return inserted


def main():
    init_db()
    logger.info("=== Stage 1: Story Generation ===")

    # Load model once for all sources
    load_model(MODEL)

    total = 0
    for source_name, source_desc in SOURCES:
        count = generate_stories(source_name, source_desc, count=10)
        total += count
        logger.info(f"  → {count} stories from {source_name}")

    # CRITICAL: Unload model to free RAM for next stage
    unload_all()

    existing = count_by_status("PENDING")
    logger.info(f"=== Done. Generated {total} new stories. Total PENDING: {existing} ===")


if __name__ == "__main__":
    main()
