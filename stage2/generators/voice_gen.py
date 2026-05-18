"""Voice narration generator using Kokoro TTS (runs on CPU, ~300MB RAM)."""

import os
from shared.logger import setup_logger
from config.settings import TTS_VOICE, TTS_SPEED

logger = setup_logger("voice_gen")


def generate_narration(scenes: list, output_path: str):
    """Generate narration audio from scene texts using Kokoro TTS."""
    from kokoro_onnx import Kokoro
    import soundfile as sf

    # Kokoro auto-downloads model on first run (~80MB)
    kokoro = Kokoro("kokoro-v1.0.onnx", "voices-v1.0.bin")

    # Build full narration with pauses between scenes
    texts = [scene["narration_text"] for scene in scenes]
    full_text = " ... ".join(texts)

    logger.info(f"  Generating narration: {len(full_text)} chars, ~{len(full_text)//150} min")

    samples, sample_rate = kokoro.create(
        full_text,
        voice=TTS_VOICE,
        speed=TTS_SPEED,
        lang="en-us"
    )

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    sf.write(output_path, samples, sample_rate)
    logger.info(f"  ✓ Saved narration to {output_path}")
