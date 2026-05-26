#!/usr/bin/env python3
"""Test the auto-generation flow end-to-end.

Simulates a story with:
- Known characters (Rama, Sita) → should be found in database, NOT regenerated
- An unknown character (Tataki) → should be auto-generated
- A generic word (villagers) → should be skipped

Usage:
    python3 tests/test_character_autogen.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.character_store import CharacterStore
from shared.character_generator import ensure_characters_exist


def test_autogen():
    print("=" * 60)
    print("Test: Character Auto-Generation Flow")
    print("=" * 60)

    # Create a fresh store
    store = CharacterStore()
    initial_stats = store.stats()
    print(f"\nInitial database: {initial_stats['total_characters']} characters, {initial_stats['total_aliases']} aliases")

    # Simulate a story with a mix of known and unknown characters
    fake_story = {
        "title": "The Wise Sage and the River",
        "source": "Ramayana - Aranya Kanda",
        "characters": ["Rama", "Sita", "Agastya", "Lopamudra", "villagers"],
        "full_story": (
            "Long ago, during their exile in the forest, Lord Rama and Sita were "
            "traveling through the beautiful Dandaka forest. They came upon the ashram "
            "of the great sage Agastya. The sage welcomed them warmly and his wife "
            "Lopamudra offered them fruits and water. Agastya gave Rama the divine "
            "bow Brahmadanda and told him about the challenges ahead. The villagers "
            "nearby were troubled by demons. Rama promised to protect them."
        ),
        "moral": "Respect your elders and seek wisdom from the wise.",
        "tags": ["exile", "forest", "sage"]
    }

    characters = fake_story["characters"]
    print(f"\nStory characters: {characters}")
    print()

    # Check who exists BEFORE auto-generation
    print("--- Pre-check ---")
    for name in characters:
        exists = store.has_character(name)
        print(f"  {'✓ EXISTS' if exists else '✗ MISSING'}: {name}")

    # Run the auto-generation
    print("\n--- Running ensure_characters_exist() ---")
    newly_generated = ensure_characters_exist(characters, fake_story, store)

    # Check who exists AFTER auto-generation
    print("\n--- Post-check ---")
    for name in characters:
        exists = store.has_character(name)
        print(f"  {'✓ EXISTS' if exists else '✗ MISSING/SKIPPED'}: {name}")

    print(f"\nNewly generated: {newly_generated}")

    # Verify the new character is lookupable
    if newly_generated:
        print("\n--- Lookup Test ---")
        for name in newly_generated:
            result = store.lookup(name)
            if result:
                print(f"  ✓ lookup('{name}') → {result['name']} ({result['timeline_stage']})")
                print(f"    Physical: {result['physical_description'][:100]}...")
                print(f"    Voice: {result['voice_description'][:100]}...")
            else:
                print(f"  ✗ lookup('{name}') → NOT FOUND (error!)")

    # Test duplicate prevention: run AGAIN with the same characters
    print("\n--- Duplicate Prevention Test ---")
    print("Running ensure_characters_exist() AGAIN with the same story...")
    newly_generated_2 = ensure_characters_exist(characters, fake_story, store)
    if not newly_generated_2:
        print("  ✓ PASS: No duplicates generated on second run!")
    else:
        print(f"  ✗ FAIL: Generated duplicates: {newly_generated_2}")

    # Final stats
    final_stats = store.stats()
    print(f"\nFinal database: {final_stats['total_characters']} characters, {final_stats['total_aliases']} aliases")
    new_count = final_stats['total_characters'] - initial_stats['total_characters']
    print(f"Characters added: {new_count}")

    # Check auto_generated directory
    auto_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data", "characters", "auto_generated"
    )
    if os.path.exists(auto_dir):
        files = [f for f in os.listdir(auto_dir) if f.endswith('.json') and not f.startswith('_')]
        print(f"\nAuto-generated files in {auto_dir}:")
        for f in sorted(files):
            print(f"  📄 {f}")

    print(f"\n{'='*60}")
    print("✅ Test complete!")
    print(f"{'='*60}")


if __name__ == "__main__":
    test_autogen()
