"""Subtitle generator using Faster-Whisper (CPU, ~500MB RAM)."""

import os
from shared.logger import setup_logger

logger = setup_logger("subtitles")


def _format_timestamp(seconds: float) -> str:
    """Convert seconds to SRT timestamp format."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def generate_subtitles(audio_path: str, srt_path: str):
    """Transcribe audio to SRT subtitles using Faster-Whisper."""
    from faster_whisper import WhisperModel

    # Use "base" model for speed on CPU, "small" for better accuracy
    model = WhisperModel("base", device="cpu", compute_type="int8")

    logger.info(f"  Transcribing: {audio_path}")
    segments, info = model.transcribe(audio_path, language="en")

    os.makedirs(os.path.dirname(srt_path), exist_ok=True)
    with open(srt_path, "w") as f:
        for i, seg in enumerate(segments, 1):
            f.write(f"{i}\n")
            f.write(f"{_format_timestamp(seg.start)} --> {_format_timestamp(seg.end)}\n")
            f.write(f"{seg.text.strip()}\n\n")

    logger.info(f"  ✓ Subtitles saved to {srt_path}")

    # Model gets garbage collected when function returns → frees RAM
