"""Character Store: loads mythological character descriptions for AI generation.

Provides O(1) lookup by character name or alias, returning timeline-appropriate
physical appearance, voice, and cinematic prompts for injection into scene
scripting and image/audio generation.

Usage:
    from shared.character_store import CharacterStore
    cs = CharacterStore()
    desc = cs.lookup("Rama", timeline_hint="exile")
    print(desc["visual_prompt"])
    print(desc["audio_prompt"])
"""

import os
import json
import glob
import re
from typing import Optional
from shared.logger import setup_logger

logger = setup_logger("character_store")

# Base path for character JSON files
CHARACTERS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "characters"
)
INDEX_FILE = os.path.join(CHARACTERS_DIR, "_index.json")


class CharacterStore:
    """Loads and indexes all character JSON files for fast name/alias lookup."""

    def __init__(self, characters_dir: str = CHARACTERS_DIR):
        self.characters_dir = characters_dir
        self._index = {}       # alias (lowercase) -> {"file": path, "key": CHARACTER_KEY}
        self._cache = {}       # file path -> parsed JSON
        self._load_index()

    def _load_index(self):
        """Load the master index, or build one from scanning all JSON files."""
        if os.path.exists(INDEX_FILE):
            try:
                with open(INDEX_FILE, "r", encoding="utf-8") as f:
                    idx = json.load(f)
                for entry in idx.get("characters", []):
                    for alias in entry.get("aliases", []):
                        self._index[alias.lower().strip()] = {
                            "file": os.path.join(self.characters_dir, entry["file"]),
                            "key": entry["key"]
                        }
                    # Also index the primary name
                    self._index[entry["name"].lower().strip()] = {
                        "file": os.path.join(self.characters_dir, entry["file"]),
                        "key": entry["key"]
                    }
                logger.info(f"Loaded character index: {len(self._index)} aliases → {len(idx['characters'])} characters")
                return
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Failed to load index file, rebuilding: {e}")

        # Fallback: scan all JSON files
        self._build_index_from_files()

    def _build_index_from_files(self):
        """Scan all character JSON files and build an in-memory index."""
        pattern = os.path.join(self.characters_dir, "**", "*.json")
        files = glob.glob(pattern, recursive=True)
        count = 0
        for filepath in files:
            basename = os.path.basename(filepath)
            if basename.startswith("_"):
                continue  # Skip _schema.json, _index.json
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for key, char_data in data.items():
                    meta = char_data.get("metadata", {})
                    name = meta.get("name", key)
                    aliases = meta.get("aliases", [])
                    rel_path = os.path.relpath(filepath, self.characters_dir)
                    entry = {"file": filepath, "key": key}

                    # Index primary name
                    self._index[name.lower().strip()] = entry
                    # Index all aliases
                    for alias in aliases:
                        self._index[alias.lower().strip()] = entry
                    # Index the KEY itself
                    self._index[key.lower().strip()] = entry
                    count += 1
            except (json.JSONDecodeError, Exception) as e:
                logger.warning(f"Skipping invalid character file {filepath}: {e}")

        logger.info(f"Built character index from files: {len(self._index)} aliases → {count} characters")

    def _load_character_file(self, filepath: str) -> dict:
        """Load and cache a character JSON file."""
        if filepath not in self._cache:
            with open(filepath, "r", encoding="utf-8") as f:
                self._cache[filepath] = json.load(f)
        return self._cache[filepath]

    def register_character(self, filepath: str, key: str, name: str, aliases: list):
        """Hot-register a new character into the index without full reload.

        Called by character_generator after auto-generating a new character
        profile. Adds the character to the in-memory index immediately so
        it's available for lookup in the same pipeline run.

        Args:
            filepath: Absolute path to the saved JSON file
            key: The CHARACTER_KEY in the JSON (e.g., 'SHABARI')
            name: Primary display name
            aliases: List of alternative names
        """
        entry = {"file": filepath, "key": key}
        self._index[name.lower().strip()] = entry
        self._index[key.lower().strip()] = entry
        for alias in aliases:
            self._index[alias.lower().strip()] = entry
        # Clear cache so next lookup reads fresh file
        self._cache.pop(filepath, None)
        logger.info(f"Hot-registered character: {name} ({key}) with {len(aliases)} aliases")

    def has_character(self, name: str) -> bool:
        """Check if a character exists by name or alias."""
        return name.lower().strip() in self._index

    def get_full_profile(self, name: str) -> Optional[dict]:
        """Get the complete character profile (all timelines)."""
        key = name.lower().strip()
        if key not in self._index:
            return None
        entry = self._index[key]
        data = self._load_character_file(entry["file"])
        return data.get(entry["key"])

    def lookup(self, name: str, timeline_hint: str = None) -> Optional[dict]:
        """Look up a character and return a flattened description dict.

        Args:
            name: Character name or alias (case-insensitive)
            timeline_hint: Optional keyword to match timeline stage
                          (e.g., "youth", "exile", "war", "old")

        Returns:
            Dict with keys: name, gender, visual_prompt, audio_prompt,
            physical_description, voice_description, wardrobe_description,
            timeline_stage, age_approximation
            — or None if character not found.
        """
        profile = self.get_full_profile(name)
        if not profile:
            return None

        meta = profile.get("metadata", {})
        timelines = profile.get("timelines", [])

        if not timelines:
            return {
                "name": meta.get("name", name),
                "gender": meta.get("gender", "Unknown"),
                "visual_prompt": "",
                "audio_prompt": "",
                "physical_description": "",
                "voice_description": "",
                "wardrobe_description": "",
                "timeline_stage": "Unknown",
                "age_approximation": 0
            }

        # Pick best matching timeline
        timeline = self._match_timeline(timelines, timeline_hint)
        phys = timeline.get("physical_appearance", {})
        voice = timeline.get("audio_and_voice_characteristics", {})
        wardrobe = timeline.get("wardrobe_and_adornments", {})
        prompts = timeline.get("cinematic_generation_prompts", {})

        # Build flattened physical description string
        phys_parts = []
        for field in ["skin_tone", "height", "build", "facial_features", "hair", "distinguishing_marks"]:
            if phys.get(field):
                phys_parts.append(phys[field])
        physical_desc = ". ".join(phys_parts)

        # Build flattened voice description string
        voice_parts = []
        for field in ["tone", "pitch", "speech_style", "emotional_baseline"]:
            if voice.get(field):
                voice_parts.append(voice[field])
        voice_desc = ". ".join(voice_parts)

        # Build wardrobe description
        ward_parts = []
        for field in ["clothing", "jewelry", "weapons_carried"]:
            if wardrobe.get(field):
                ward_parts.append(wardrobe[field])
        wardrobe_desc = ". ".join(ward_parts)

        return {
            "name": meta.get("name", name),
            "gender": meta.get("gender", "Unknown"),
            "visual_prompt": prompts.get("visual_prompt", ""),
            "audio_prompt": prompts.get("audio_prompt", ""),
            "physical_description": physical_desc,
            "voice_description": voice_desc,
            "wardrobe_description": wardrobe_desc,
            "timeline_stage": timeline.get("timeline_stage", ""),
            "age_approximation": timeline.get("age_approximation", 0)
        }

    def _match_timeline(self, timelines: list, hint: str = None) -> dict:
        """Pick the best matching timeline based on a keyword hint."""
        if not hint or len(timelines) == 1:
            # Default: pick the middle timeline (most representative)
            return timelines[len(timelines) // 2]

        hint_lower = hint.lower()
        # Score each timeline by keyword overlap
        best_score = -1
        best_tl = timelines[0]
        for tl in timelines:
            stage = tl.get("timeline_stage", "").lower()
            context = tl.get("context_description", "").lower()
            text = f"{stage} {context}"
            score = sum(1 for word in hint_lower.split() if word in text)
            if score > best_score:
                best_score = score
                best_tl = tl
        return best_tl

    def get_scene_character_descriptions(self, character_names: list,
                                          timeline_hint: str = None) -> str:
        """Build a combined character description block for scene prompts.

        Args:
            character_names: List of character names mentioned in a scene
            timeline_hint: Context hint for timeline selection

        Returns:
            Formatted string block describing all characters, ready to inject
            into image/video generation prompts.
        """
        descriptions = []
        for name in character_names:
            desc = self.lookup(name, timeline_hint)
            if desc:
                block = (
                    f"[{desc['name']}]: "
                    f"{desc['physical_description']} "
                    f"Wearing: {desc['wardrobe_description']}"
                )
                descriptions.append(block)
            else:
                logger.debug(f"Character not found in database: {name}")

        if not descriptions:
            return ""

        return "CHARACTER APPEARANCES:\n" + "\n".join(descriptions)

    def get_voice_casting(self, character_names: list,
                           timeline_hint: str = None) -> dict:
        """Build voice casting info for characters in a scene.

        Returns:
            Dict mapping character name -> voice description string
        """
        casting = {}
        for name in character_names:
            desc = self.lookup(name, timeline_hint)
            if desc and desc["voice_description"]:
                casting[desc["name"]] = desc["voice_description"]
        return casting

    def list_all_characters(self) -> list:
        """List all unique character names in the database."""
        seen = set()
        names = []
        for alias, entry in self._index.items():
            key = entry["key"]
            if key not in seen:
                seen.add(key)
                profile = self.get_full_profile(alias)
                if profile:
                    names.append(profile.get("metadata", {}).get("name", key))
        return sorted(names)

    def stats(self) -> dict:
        """Return statistics about the character database."""
        seen_keys = set()
        total_timelines = 0
        epics = {"Ramayana": 0, "Mahabharata": 0, "Both": 0}

        for alias, entry in self._index.items():
            key = entry["key"]
            if key in seen_keys:
                continue
            seen_keys.add(key)
            profile = self.get_full_profile(alias)
            if profile:
                total_timelines += len(profile.get("timelines", []))
                epic = profile.get("metadata", {}).get("epic", "Unknown")
                if epic in epics:
                    epics[epic] += 1

        return {
            "total_characters": len(seen_keys),
            "total_aliases": len(self._index),
            "total_timelines": total_timelines,
            "by_epic": epics
        }


# Module-level singleton for convenience
_store = None

def get_store() -> CharacterStore:
    """Get or create the global CharacterStore singleton."""
    global _store
    if _store is None:
        _store = CharacterStore()
    return _store
