import os
from typing import Any, Dict

from core.ai_engine import generate_content

from .content_builder import build_filename, build_markdown, slugify
from .media_utils import get_audio_filepath, get_image_filepaths
from .publisher import publish_images, publish_post


def run() -> Dict[str, Any]:
    input_folder = os.getenv("GH_INPUT_FOLDER", "media-input")
    content_dir = os.getenv("ASTRO_CONTENT_DIR", "content/blog")
    assets_dir = os.getenv("ASTRO_ASSETS_DIR", "public/images/blog")

    audio_path = get_audio_filepath(input_folder)
    if not audio_path:
        raise FileNotFoundError(f"No audio file found in folder '{input_folder}'.")

    image_paths = get_image_filepaths(input_folder)

    print("[Pipeline] Generating content from audio via AI provider...")
    result = generate_content(audio_path, image_paths)

    slug = slugify(result.title)
    published_images = publish_images(image_paths, slug, assets_dir)
    hero_image = published_images[0] if published_images else None
    extra_images = published_images[1:] if len(published_images) > 1 else []

    markdown = build_markdown(result, hero_image=hero_image, extra_images=extra_images)
    filename = build_filename(result.title)
    filepath = publish_post(filename, markdown, content_dir)

    print(f"[Pipeline] Astro post written to '{filepath}'.")
    return {
        "status": "completed",
        "file_path": filepath,
        "title": result.title,
        "tags": result.tags,
        "images": published_images,
    }
