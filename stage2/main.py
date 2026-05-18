"""Stage 2 Orchestrator: Sequential processing with RAM management.

Picks one PENDING story, runs validation → scripting → media → assembly.
Each step loads its model, does work, then unloads before the next step.
Designed for 16GB Mac — only one heavy model in RAM at a time.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.db import get_next_by_status, update_status
from shared.ollama_utils import load_model, unload_all
from shared.logger import setup_logger
from config.settings import STORY_MODEL, OUTPUT_DIR

logger = setup_logger("stage2")


def process_one_story():
    """Process a single story through the full Stage 2 pipeline."""

    # Get next pending story
    story = get_next_by_status("PENDING")
    if not story:
        logger.info("No PENDING stories found.")
        return False

    story_id = story["id"]
    logger.info(f"Processing story #{story_id}: {story['title']}")

    # Create output directory
    story_dir = os.path.join(OUTPUT_DIR, str(story_id))
    os.makedirs(os.path.join(story_dir, "images"), exist_ok=True)
    os.makedirs(os.path.join(story_dir, "audio"), exist_ok=True)
    os.makedirs(os.path.join(story_dir, "video"), exist_ok=True)

    # ── Step 1: Validate (LLM + Web Search) ──────────────────────
    logger.info("Step 1/6: Validation")
    load_model(STORY_MODEL)
    try:
        from stage2.agents.validator import validate_story
        result = validate_story(story)
        update_status(story_id, "VALIDATED" if result["approved"] else "REJECTED",
                      validation_result=result)
        if not result["approved"]:
            logger.warning(f"Story REJECTED: {result.get('reason', 'unknown')}")
            unload_all()
            return True
    except Exception as e:
        logger.error(f"Validation failed: {e}")
        unload_all()
        return False
    logger.info("  ✓ Validated")

    # ── Step 2: Scene Scripting (LLM) ────────────────────────────
    logger.info("Step 2/6: Scene Scripting")
    # Model already loaded from step 1
    try:
        from stage2.generators.scripter import generate_scenes
        scenes = generate_scenes(story)
        update_status(story_id, "SCRIPTED", scenes=scenes)
    except Exception as e:
        logger.error(f"Scripting failed: {e}")
        unload_all()
        return False
    unload_all()  # FREE RAM — done with LLM
    logger.info(f"  ✓ {len(scenes)} scenes scripted")

    # ── Step 3: Image Generation (No LLM needed) ─────────────────
    logger.info("Step 3/6: Image Generation")
    # TODO: Implement ComfyUI/Colab integration
    # For now, placeholder — images generated externally
    logger.info("  ⏳ Images: generate via Colab notebook (see PLAN.md)")

    # ── Step 4: Voice Narration (Kokoro TTS, CPU only ~300MB) ────
    logger.info("Step 4/6: Voice Narration")
    try:
        from stage2.generators.voice_gen import generate_narration
        audio_path = os.path.join(story_dir, "audio", "narration.wav")
        generate_narration(scenes, audio_path)
    except Exception as e:
        logger.error(f"Voice generation failed: {e}")
        return False
    logger.info("  ✓ Narration generated")

    # ── Step 5: Subtitles (Faster-Whisper, CPU ~500MB) ───────────
    logger.info("Step 5/6: Subtitles")
    try:
        from stage2.assembly.subtitles import generate_subtitles
        srt_path = os.path.join(story_dir, "audio", "subtitles.srt")
        generate_subtitles(audio_path, srt_path)
    except Exception as e:
        logger.error(f"Subtitle generation failed: {e}")
        return False
    logger.info("  ✓ Subtitles generated")

    # ── Step 6: Video Assembly (MoviePy + FFmpeg, CPU) ───────────
    logger.info("Step 6/6: Video Assembly")
    # TODO: Implement after images are ready
    # from stage2.assembly.video_builder import assemble_video
    # assemble_video(story_id, scenes)
    logger.info("  ⏳ Assembly: waiting for images")

    update_status(story_id, "ASSEMBLED")
    logger.info(f"=== Story #{story_id} complete ===")
    return True


def main():
    logger.info("=== Stage 2: Daily Processing ===")
    process_one_story()


if __name__ == "__main__":
    main()
