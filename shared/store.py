"""File-based story store. Stories are JSON files organized by status folders.

Structure:
  output/stories/pending/0001_hanumans_leap.json
  output/stories/validated/0001_hanumans_leap.json
  output/stories/scripted/0001_hanumans_leap.json
  ...

Status change = move file to next folder.
Dedup = check if title slug exists across all folders.
"""

import os
import json
import re
import shutil
import glob
from config.settings import OUTPUT_DIR
from shared.logger import setup_logger

logger = setup_logger("store")

STORIES_DIR = os.path.join(OUTPUT_DIR, "stories")
MEDIA_DIR = os.path.join(OUTPUT_DIR, "media")
STATUSES = ["pending", "validated", "scripted", "assembled", "published", "rejected"]


def _ensure_dirs():
    """Create all status folders if they don't exist."""
    for status in STATUSES:
        os.makedirs(os.path.join(STORIES_DIR, status), exist_ok=True)
    os.makedirs(MEDIA_DIR, exist_ok=True)


def _slugify(title: str) -> str:
    """Convert title to filesystem-safe slug."""
    slug = title.lower().strip()
    slug = re.sub(r'[^a-z0-9]+', '_', slug)
    slug = slug.strip('_')
    return slug[:60]  # Cap length


def _get_next_index() -> int:
    """Find the highest existing index across all folders and return next."""
    max_idx = 0
    for status in STATUSES:
        folder = os.path.join(STORIES_DIR, status)
        if not os.path.exists(folder):
            continue
        for f in os.listdir(folder):
            if f.endswith(".json"):
                try:
                    idx = int(f[:4])
                    max_idx = max(max_idx, idx)
                except ValueError:
                    pass
    return max_idx + 1


def _find_story_file(index: int) -> str | None:
    """Find a story file by index across all status folders."""
    prefix = f"{index:04d}_"
    for status in STATUSES:
        folder = os.path.join(STORIES_DIR, status)
        if not os.path.exists(folder):
            continue
        for f in os.listdir(folder):
            if f.startswith(prefix) and f.endswith(".json"):
                return os.path.join(folder, f)
    return None


def get_all_titles() -> set:
    """Return all existing story titles (lowercase) for dedup."""
    titles = set()
    for status in STATUSES:
        folder = os.path.join(STORIES_DIR, status)
        if not os.path.exists(folder):
            continue
        for f in os.listdir(folder):
            if f.endswith(".json"):
                # Extract title from filename: 0001_some_title.json → some_title
                title_part = f[5:-5]  # Remove "0001_" prefix and ".json" suffix
                titles.add(title_part)
    return titles


def save_story(story: dict) -> str:
    """Save a new story to pending/. Returns the filename."""
    _ensure_dirs()
    idx = _get_next_index()
    slug = _slugify(story["title"])
    filename = f"{idx:04d}_{slug}.json"
    filepath = os.path.join(STORIES_DIR, "pending", filename)

    # Add index to the story data
    story["id"] = idx
    story["status"] = "pending"

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(story, f, indent=2, ensure_ascii=False)

    # Create media directory for this story
    os.makedirs(os.path.join(MEDIA_DIR, f"{idx:04d}_{slug}", "images"), exist_ok=True)
    os.makedirs(os.path.join(MEDIA_DIR, f"{idx:04d}_{slug}", "audio"), exist_ok=True)
    os.makedirs(os.path.join(MEDIA_DIR, f"{idx:04d}_{slug}", "video"), exist_ok=True)

    return filename


def move_status(filename: str, from_status: str, to_status: str):
    """Move a story file from one status folder to another."""
    src = os.path.join(STORIES_DIR, from_status, filename)
    dst_dir = os.path.join(STORIES_DIR, to_status)
    os.makedirs(dst_dir, exist_ok=True)
    dst = os.path.join(dst_dir, filename)

    # Update status inside the JSON too
    with open(src, "r", encoding="utf-8") as f:
        story = json.load(f)
    story["status"] = to_status
    with open(src, "w", encoding="utf-8") as f:
        json.dump(story, f, indent=2, ensure_ascii=False)

    shutil.move(src, dst)
    logger.info(f"  {from_status} → {to_status}: {filename}")


def get_next_pending() -> tuple[dict, str] | None:
    """Get the first story in pending/. Returns (story_dict, filename) or None."""
    folder = os.path.join(STORIES_DIR, "pending")
    if not os.path.exists(folder):
        return None
    files = sorted(f for f in os.listdir(folder) if f.endswith(".json"))
    if not files:
        return None
    filepath = os.path.join(folder, files[0])
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f), files[0]


def read_story(filename: str, status: str) -> dict:
    """Read a story JSON by filename and status folder."""
    filepath = os.path.join(STORIES_DIR, status, filename)
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def update_story(filename: str, status: str, updates: dict):
    """Update fields in a story JSON file."""
    filepath = os.path.join(STORIES_DIR, status, filename)
    with open(filepath, "r", encoding="utf-8") as f:
        story = json.load(f)
    story.update(updates)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(story, f, indent=2, ensure_ascii=False)


def count_by_status(status: str) -> int:
    """Count stories in a status folder."""
    folder = os.path.join(STORIES_DIR, status)
    if not os.path.exists(folder):
        return 0
    return len([f for f in os.listdir(folder) if f.endswith(".json")])


def get_media_dir(filename: str) -> str:
    """Get the media directory path for a story."""
    slug = filename[:-5]  # Remove .json
    return os.path.join(MEDIA_DIR, slug)


# Auto-create dirs on import
_ensure_dirs()
