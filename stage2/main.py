"""Stage 2 Orchestrator: Sequential processing with RAM management.

Picks one pending story, runs validation → scripting → media → assembly.
Each step loads its model, does work, then unloads before the next step.
Designed for 16GB Mac — only one heavy model in RAM at a time.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.store import get_next_pending, move_status, update_story, get_media_dir, count_by_status
from shared.ollama_utils import load_model, unload_all
from shared.logger import setup_logger
from config.settings import STORY_MODEL

logger = setup_logger("stage2")


def process_one_story():
    """Process a single story through the full Stage 2 pipeline."""

    result = get_next_pending()
    if not result:
        logger.info("No pending stories found.")
        return False

    story, filename = result
    story_id = story["id"]
    media_dir = get_media_dir(filename)
    logger.info(f"Processing story #{story_id:04d}: {story['title']}")

    # ── Step 1: Validate (LLM + RAG + Web Search) ────────────────
    logger.info("Step 1/6: Validation")
    load_model(STORY_MODEL)
    try:
        from stage2.agents.validator import validate_story
        result = validate_story(story, story_number=story_id)
        update_story(filename, "pending", {"validation_result": result})

        if not result["approved"]:
            move_status(filename, "pending", "rejected")
            logger.warning(f"Story REJECTED: {result.get('reason', 'unknown')}")
            unload_all()
            return True
    except Exception as e:
        logger.error(f"Validation failed: {e}")
        unload_all()
        return False

    move_status(filename, "pending", "validated")
    logger.info("  ✓ Validated")

    # ── Step 2: Scene Scripting (LLM) ────────────────────────────
    logger.info("Step 2/6: Scene Scripting")
    try:
        from stage2.generators.scripter import generate_scenes
        scenes = generate_scenes(story)
        update_story(filename, "validated", {"scenes": scenes})
        move_status(filename, "validated", "scripted")
    except Exception as e:
        logger.error(f"Scripting failed: {e}")
        unload_all()
        return False
    unload_all()  # FREE RAM — done with LLM
    logger.info(f"  ✓ {len(scenes)} scenes scripted")

    # ── Step 3: Image Generation (No LLM needed) ─────────────────
    logger.info("Step 3/6: Image Generation")
    logger.info(f"  ⏳ Generate images via Colab → save to {media_dir}/images/")

    # ── Step 4: Voice Narration (Kokoro TTS, CPU only ~300MB) ────
    logger.info("Step 4/6: Voice Narration")
    try:
        from stage2.generators.voice_gen import generate_narration
        audio_path = os.path.join(media_dir, "audio", "narration.wav")
        generate_narration(scenes, audio_path)
    except Exception as e:
        logger.error(f"Voice generation failed: {e}")
        return False
    logger.info("  ✓ Narration generated")

    # ── Step 5: Subtitles (Faster-Whisper, CPU ~500MB) ───────────
    logger.info("Step 5/6: Subtitles")
    try:
        from stage2.assembly.subtitles import generate_subtitles
        srt_path = os.path.join(media_dir, "audio", "subtitles.srt")
        generate_subtitles(audio_path, srt_path)
    except Exception as e:
        logger.error(f"Subtitle generation failed: {e}")
        return False
    logger.info("  ✓ Subtitles generated")

    # ── Step 6: Video Assembly (MoviePy + FFmpeg, CPU) ───────────
    logger.info("Step 6/6: Video Assembly")
    # TODO: Implement after images are ready
    logger.info("  ⏳ Assembly: waiting for images")

    move_status(filename, "scripted", "assembled")
    logger.info(f"=== Story #{story_id:04d} complete ===")
    return True


def main():
    logger.info("=== Stage 2: Daily Processing ===")
    logger.info(f"Pending: {count_by_status('pending')} stories")
    process_one_story()


if __name__ == "__main__":
    main()
