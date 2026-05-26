#!/usr/bin/env python3
"""Build the master _index.json from all character JSON files.

Usage:
    python3 data/characters/build_index.py
"""

import json
import os
import glob

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INDEX_FILE = os.path.join(BASE_DIR, "_index.json")


def build_index():
    pattern = os.path.join(BASE_DIR, "**", "*.json")
    files = glob.glob(pattern, recursive=True)
    
    characters = []
    stats = {"total": 0, "ramayana": 0, "mahabharata": 0, "total_timelines": 0}
    
    for filepath in sorted(files):
        basename = os.path.basename(filepath)
        if basename.startswith("_") or basename.startswith("generate") or basename == "build_index.py":
            continue
        
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, Exception) as e:
            print(f"  ✗ Skipping {basename}: {e}")
            continue
        
        for key, char_data in data.items():
            meta = char_data.get("metadata", {})
            timelines = char_data.get("timelines", [])
            rel_path = os.path.relpath(filepath, BASE_DIR)
            
            entry = {
                "character_id": meta.get("character_id", ""),
                "key": key,
                "name": meta.get("name", key),
                "aliases": meta.get("aliases", []),
                "epic": meta.get("epic", ""),
                "gender": meta.get("gender", ""),
                "primary_role": meta.get("primary_role", ""),
                "tags": meta.get("tags", []),
                "file": rel_path,
                "timeline_count": len(timelines),
                "timeline_stages": [t.get("timeline_stage", "") for t in timelines]
            }
            characters.append(entry)
            
            stats["total"] += 1
            stats["total_timelines"] += len(timelines)
            epic = meta.get("epic", "")
            if "Ramayana" in epic:
                stats["ramayana"] += 1
            elif "Mahabharata" in epic:
                stats["mahabharata"] += 1
    
    index = {
        "_description": "Master index of all mythological character files in the database",
        "_generated": True,
        "_rebuild": "python3 data/characters/build_index.py",
        "stats": stats,
        "characters": characters
    }
    
    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'='*60}")
    print(f"Character Database Index")
    print(f"{'='*60}")
    print(f"Total characters: {stats['total']}")
    print(f"  Ramayana:     {stats['ramayana']}")
    print(f"  Mahabharata:  {stats['mahabharata']}")
    print(f"Total timelines: {stats['total_timelines']}")
    print(f"Index written to: {INDEX_FILE}")
    print(f"{'='*60}")
    
    return stats


if __name__ == "__main__":
    build_index()
