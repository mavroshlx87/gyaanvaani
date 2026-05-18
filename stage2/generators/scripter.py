"""Scene scripter: breaks a story into 15-20 visual scenes with image prompts."""

import json
import re
import ollama
from shared.logger import setup_logger
from config.settings import STORY_MODEL

logger = setup_logger("scripter")

SCENE_PROMPT = """Break this children's story into exactly 18 visual scenes for an animated storybook video.

STORY:
{story}

For each scene output JSON array:
[{{
  "scene_number": 1,
  "narration_text": "what the narrator says for this scene",
  "image_prompt": "3D Pixar style, [detailed visual description], vibrant colors, soft lighting, child-friendly, 16:9",
  "duration_seconds": 25,
  "camera_motion": "slow_zoom_in"
}}]

RULES:
- 18 scenes, 20-30 seconds each (total ~7-8 min)
- image_prompt MUST start with "3D Pixar style"
- Describe character appearance (face, clothing, colors) in EVERY image_prompt
- camera_motion: one of slow_zoom_in, slow_zoom_out, pan_left, pan_right
- Last scene must show the moral lesson visually
- Output valid JSON array only, no markdown"""


def generate_scenes(story: dict) -> list:
    """Generate scene breakdown for a story."""
    logger.info(f"  Scripting scenes for: {story['title']}")

    resp = ollama.chat(model=STORY_MODEL, messages=[{
        "role": "user",
        "content": SCENE_PROMPT.format(story=story["full_story"][:3000])
    }], options={"temperature": 0.7, "num_ctx": 8192})

    raw = resp["message"]["content"]
    # Clean thinking tags
    raw = re.sub(r'<think>.*?</think>', '', raw, flags=re.DOTALL).strip()
    # Remove markdown fences
    if raw.startswith("```"):
        raw = re.sub(r'^```(?:json)?\s*\n?', '', raw)
        raw = re.sub(r'\n?```\s*$', '', raw)

    try:
        scenes = json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r'\[.*\]', raw, re.DOTALL)
        if match:
            scenes = json.loads(match.group())
        else:
            raise ValueError(f"Could not parse scenes JSON: {raw[:300]}")

    logger.info(f"  Generated {len(scenes)} scenes")
    return scenes
