import os

# Paths
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")
ASSETS_DIR = os.path.join(PROJECT_ROOT, "assets")

# Ollama
OLLAMA_URL = "http://localhost:11434"
STORY_MODEL = "qwen3:8b"
VALIDATION_MODEL = "qwen3:8b"  # Use same model to save RAM

# TTS
TTS_VOICE = "af_heart"
TTS_SPEED = 0.9

# Video
VIDEO_FPS = 24
VIDEO_WIDTH = 1920
VIDEO_HEIGHT = 1080
REEL_WIDTH = 1080
REEL_HEIGHT = 1920
BGM_VOLUME = 0.15

# Publishing
YOUTUBE_CATEGORY = "24"  # Entertainment
MADE_FOR_KIDS = True
