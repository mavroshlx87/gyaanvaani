import requests
import logging

logger = logging.getLogger(__name__)
OLLAMA_URL = "http://localhost:11434"


def load_model(model: str):
    """Preload model into RAM."""
    logger.info(f"Loading model: {model}")
    requests.post(f"{OLLAMA_URL}/api/generate",
                  json={"model": model, "prompt": "", "keep_alive": "10m"})


def unload_model(model: str):
    """Force unload model from RAM (critical for 16GB Mac)."""
    logger.info(f"Unloading model: {model}")
    requests.post(f"{OLLAMA_URL}/api/generate",
                  json={"model": model, "prompt": "", "keep_alive": 0})


def unload_all():
    """Unload all loaded models from RAM."""
    try:
        resp = requests.get(f"{OLLAMA_URL}/api/ps")
        for m in resp.json().get("models", []):
            unload_model(m["name"])
        logger.info("All models unloaded")
    except Exception as e:
        logger.warning(f"Failed to unload models: {e}")
