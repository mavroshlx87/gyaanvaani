"""Image generation placeholder — uses Google Colab free tier for FLUX.1-dev."""

# NOTE: Image generation for 16GB Mac without GPU requires external compute.
# Use the Google Colab notebook workflow below.
#
# WORKFLOW:
# 1. Run stage2/main.py up to step 2 (scripting) to get scene prompts
# 2. Export prompts: python -c "from shared.db import *; import json; s=get_next_by_status('SCRIPTED'); print(json.dumps(s['scenes'], indent=2))"
# 3. Open Google Colab → load FLUX.1-dev GGUF Q5 notebook
# 4. Paste prompts, generate 18 images (16:9) + 5 images (9:16 for reel)
# 5. Download to output/{story_id}/images/
# 6. Resume stage2/main.py from step 4
#
# FUTURE: When you get a GPU, replace this with local ComfyUI + FLUX.1-dev
# or use SiliconFlow API (very cheap Chinese cloud GPU provider)

from shared.logger import setup_logger

logger = setup_logger("image_gen")


def generate_images(scenes: list, output_dir: str):
    """Placeholder: prints prompts for Colab generation."""
    logger.info("Image generation requires GPU. Use Google Colab free tier.")
    logger.info(f"Generate {len(scenes)} images and save to: {output_dir}")

    for scene in scenes:
        print(f"\n--- Scene {scene['scene_number']} ---")
        print(f"Prompt: {scene['image_prompt']}")

    logger.info("After generating images in Colab, run stage2/main.py again.")
