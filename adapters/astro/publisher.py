import os
import shutil
from typing import List, Optional, Tuple


def _root_relative(path: str, public_url_prefix: Optional[str] = None) -> str:
    """Return a leading-slash URL, optionally relative to a public assets root."""
    normalized_path = path.replace(os.sep, "/")
    if public_url_prefix:
        normalized_prefix = public_url_prefix.strip("/")
        public_marker = "/public/"
        public_index = normalized_path.rfind(public_marker)
        if public_index >= 0:
            normalized_path = normalized_path[public_index + len(public_marker):]
        if normalized_path == normalized_prefix or normalized_path.startswith(f"{normalized_prefix}/"):
            return f"/{normalized_path.lstrip('/')}"
        return f"/{normalized_prefix}/{normalized_path.lstrip('/')}".replace("//", "/")
    return "/" + normalized_path.lstrip("/")


def publish_images(
    image_paths: List[str],
    slug: str,
    assets_dir: str,
    public_url_prefix: Optional[str] = None,
) -> List[str]:
    os.makedirs(assets_dir, exist_ok=True)

    published_urls = []
    for index, image_path in enumerate(image_paths):
        ext = os.path.splitext(image_path)[1]
        dest_filename = f"{slug}-{index + 1}{ext}"
        dest_path = os.path.join(assets_dir, dest_filename)
        shutil.copyfile(image_path, dest_path)
        published_urls.append(_root_relative(dest_path, public_url_prefix))

    return published_urls


def publish_post(filename: str, markdown: str, content_dir: str) -> str:
    os.makedirs(content_dir, exist_ok=True)
    filepath = os.path.join(content_dir, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(markdown)
    return filepath
