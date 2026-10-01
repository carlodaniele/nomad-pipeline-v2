import json
import os
import re
from typing import Any, Dict

from core.ai_engine import generate_content

from .content_builder import build_filename, build_markdown, slugify
from .media_utils import get_audio_filepath, get_image_filepaths
from .publisher import publish_images, publish_post


def run() -> Dict[str, Any]:
    input_folder = os.getenv("GH_INPUT_FOLDER", "media-input")
    content_dir = os.getenv("ASTRO_CONTENT_DIR", "content/blog")
    assets_dir = os.getenv("ASTRO_ASSETS_DIR", "public/images/blog")
    asset_url_prefix = os.getenv("ASTRO_ASSET_URL_PREFIX")

    audio_path = get_audio_filepath(input_folder)
    if not audio_path:
        raise FileNotFoundError(f"No audio file found in folder '{input_folder}'.")

    metadata_path = f"{audio_path}.json"
    journey_id = ""
    if os.path.exists(metadata_path):
        with open(metadata_path, "r", encoding="utf-8") as metadata_file:
            journey_id = json.load(metadata_file)["journey_id"].strip()

    if journey_id:
        if not re.fullmatch(r"[0-9]{4}-[a-z0-9]+(?:-[a-z0-9]+)*", journey_id):
            raise ValueError(f"Invalid JOURNEY_ID: {journey_id!r}")
        journeys_dir = os.getenv("ASTRO_JOURNEYS_DIR", "astro-site/src/content/journeys")
        if not os.path.isdir(journeys_dir):
            raise FileNotFoundError(f"Astro journeys directory unavailable: {journeys_dir}")
        if not os.path.isfile(os.path.join(journeys_dir, f"{journey_id}.md")):
            raise ValueError(f"Unknown JOURNEY_ID in Astro repository: {journey_id}")

    image_paths = get_image_filepaths(input_folder)

    print("[Pipeline] Generating content from audio via AI provider...")
    result = generate_content(audio_path, image_paths)

    slug = slugify(result.title)
    published_images = publish_images(
        image_paths,
        slug,
        assets_dir,
        asset_url_prefix=asset_url_prefix,
    )
    hero_image = published_images[0] if published_images else None
    extra_images = published_images[1:] if len(published_images) > 1 else []

    markdown = build_markdown(result, hero_image=hero_image, extra_images=extra_images, journey_id=journey_id)
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
