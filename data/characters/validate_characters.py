#!/usr/bin/env python3
"""Validate all character JSON files in the database.

Checks:
1. All JSON files parse correctly
2. Required fields are present
3. Character count
4. Timeline structure
5. Character lookup by name and alias

Usage:
    python3 data/characters/validate_characters.py
"""

import json
import os
import glob
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(BASE_DIR))
sys.path.insert(0, PROJECT_ROOT)

REQUIRED_METADATA = ["character_id", "name", "epic", "primary_role", "gender"]
REQUIRED_TIMELINE = ["timeline_stage", "age_approximation", "physical_appearance", 
                     "wardrobe_and_adornments", "audio_and_voice_characteristics",
                     "cinematic_generation_prompts"]
REQUIRED_APPEARANCE = ["skin_tone", "build", "facial_features", "hair"]
REQUIRED_PROMPTS = ["visual_prompt", "audio_prompt"]


def validate_all():
    pattern = os.path.join(BASE_DIR, "**", "*.json")
    files = glob.glob(pattern, recursive=True)
    
    total = 0
    errors = 0
    warnings = 0
    characters = []
    all_aliases = set()
    
    print("=" * 60)
    print("Character Database Validation")
    print("=" * 60)
    
    for filepath in sorted(files):
        basename = os.path.basename(filepath)
        if basename.startswith("_") or "generate" in basename or "build_index" in basename or "validate" in basename:
            continue
        
        # 1. Parse JSON
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            print(f"  ✗ PARSE ERROR: {basename} — {e}")
            errors += 1
            continue
        
        for key, char_data in data.items():
            total += 1
            meta = char_data.get("metadata", {})
            timelines = char_data.get("timelines", [])
            name = meta.get("name", key)
            char_id = meta.get("character_id", "?")
            
            # 2. Required metadata fields
            for field in REQUIRED_METADATA:
                if not meta.get(field):
                    print(f"  ✗ {char_id} {name}: missing metadata.{field}")
                    errors += 1
            
            # 3. Timelines
            if not timelines:
                print(f"  ✗ {char_id} {name}: no timelines defined")
                errors += 1
            
            for i, tl in enumerate(timelines):
                for field in REQUIRED_TIMELINE:
                    if field not in tl:
                        print(f"  ✗ {char_id} {name} timeline[{i}]: missing {field}")
                        errors += 1
                
                # Check appearance fields
                appearance = tl.get("physical_appearance", {})
                for field in REQUIRED_APPEARANCE:
                    if not appearance.get(field):
                        print(f"  ⚠ {char_id} {name} timeline[{i}]: empty appearance.{field}")
                        warnings += 1
                
                # Check prompts
                prompts = tl.get("cinematic_generation_prompts", {})
                for field in REQUIRED_PROMPTS:
                    if not prompts.get(field):
                        print(f"  ✗ {char_id} {name} timeline[{i}]: missing prompt.{field}")
                        errors += 1
            
            # 4. Collect aliases for uniqueness check
            aliases = meta.get("aliases", [])
            for alias in aliases:
                if alias.lower() in all_aliases:
                    print(f"  ⚠ {char_id} {name}: duplicate alias '{alias}'")
                    warnings += 1
                all_aliases.add(alias.lower())
            all_aliases.add(name.lower())
            
            characters.append({
                "id": char_id,
                "name": name,
                "epic": meta.get("epic", "?"),
                "timelines": len(timelines),
                "aliases": len(aliases)
            })
    
    # 5. Test character lookup
    print("\n" + "-" * 60)
    print("Testing Character Lookup Engine...")
    print("-" * 60)
    try:
        from shared.character_store import CharacterStore
        store = CharacterStore()
        
        test_lookups = ["Rama", "Sita", "Hanuman", "Arjuna", "Krishna", "Draupadi",
                       "Bhishma", "Karna", "Ravana", "Lakshmana",
                       # Test aliases
                       "Partha", "Panchali", "Bajrangbali", "Dashanan", "Pitamaha"]
        
        for name in test_lookups:
            result = store.lookup(name)
            if result:
                print(f"  ✓ lookup('{name}') → {result['name']} ({result['timeline_stage']})")
            else:
                print(f"  ✗ lookup('{name}') → NOT FOUND")
                errors += 1
        
        stats = store.stats()
        print(f"\n  Store stats: {stats}")
    except Exception as e:
        print(f"  ✗ Character store error: {e}")
        errors += 1
    
    # Summary
    print("\n" + "=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)
    print(f"Total characters: {total}")
    print(f"Total timelines:  {sum(c['timelines'] for c in characters)}")
    print(f"Errors:           {errors}")
    print(f"Warnings:         {warnings}")
    
    ramayana = sum(1 for c in characters if "Ramayana" in c["epic"])
    mahabharata = sum(1 for c in characters if "Mahabharata" in c["epic"])
    print(f"  Ramayana:      {ramayana}")
    print(f"  Mahabharata:   {mahabharata}")
    
    # Top characters by timelines
    by_timelines = sorted(characters, key=lambda c: c["timelines"], reverse=True)[:10]
    print(f"\nTop 10 characters by timeline count:")
    for c in by_timelines:
        print(f"  {c['id']:>8} {c['name']:<25} {c['timelines']} timelines, {c['aliases']} aliases")
    
    print(f"\n{'='*60}")
    if errors == 0:
        print("✅ ALL VALIDATIONS PASSED")
    else:
        print(f"❌ {errors} ERRORS FOUND — fix before production use")
    print(f"{'='*60}")
    
    return errors == 0


if __name__ == "__main__":
    success = validate_all()
    sys.exit(0 if success else 1)
