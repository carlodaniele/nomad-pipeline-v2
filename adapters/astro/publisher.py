import os
import shutil
from typing import List, Optional, Tuple


def _asset_reference(path: str, asset_url_prefix: Optional[str] = None) -> str:
    """Return a Markdown/frontmatter reference for a generated asset."""
    normalized_path = path.replace(os.sep, "/")
    filename = normalized_path.rsplit("/", 1)[-1]
    if asset_url_prefix:
        return f"{asset_url_prefix.rstrip('/')}/{filename}"
    return "/" + filename


def publish_images(
    image_paths: List[str],
    slug: str,
    assets_dir: str,
    asset_url_prefix: Optional[str] = None,
) -> List[str]:
    os.makedirs(assets_dir, exist_ok=True)

    published_urls = []
    for index, image_path in enumerate(image_paths):
        ext = os.path.splitext(image_path)[1]
        dest_filename = f"{slug}-{index + 1}{ext}"
        dest_path = os.path.join(assets_dir, dest_filename)
        shutil.copyfile(image_path, dest_path)
        published_urls.append(_asset_reference(dest_path, asset_url_prefix))

    return published_urls


def publish_post(filename: str, markdown: str, content_dir: str) -> str:
    os.makedirs(content_dir, exist_ok=True)
    filepath = os.path.join(content_dir, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(markdown)
    return filepath
