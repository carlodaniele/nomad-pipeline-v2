import os
import shutil
from typing import List, Optional, Tuple


def _root_relative(path: str) -> str:
    """Return a leading-slash, root-relative URL for use in frontmatter/markdown."""
    return "/" + path.lstrip("/")


def publish_images(image_paths: List[str], slug: str, assets_dir: str) -> List[str]:
    os.makedirs(assets_dir, exist_ok=True)

    published_urls = []
    for index, image_path in enumerate(image_paths):
        ext = os.path.splitext(image_path)[1]
        dest_filename = f"{slug}-{index + 1}{ext}"
        dest_path = os.path.join(assets_dir, dest_filename)
        shutil.copyfile(image_path, dest_path)
        published_urls.append(_root_relative(dest_path))

    return published_urls


def publish_post(filename: str, markdown: str, content_dir: str) -> str:
    os.makedirs(content_dir, exist_ok=True)
    filepath = os.path.join(content_dir, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(markdown)
    return filepath
