import mimetypes
import os
from typing import List, Optional


def get_audio_filepath(input_folder: str) -> Optional[str]:
    if not os.path.exists(input_folder):
        return None

    for filename in sorted(os.listdir(input_folder)):
        filepath = os.path.join(input_folder, filename)
        if not os.path.isfile(filepath) or filename.startswith("."):
            continue

        mime_type, _ = mimetypes.guess_type(filepath)
        mime_type = mime_type or ""
        if mime_type.startswith("audio/") or filename.lower().endswith(
            (".mp3", ".m4a", ".wav", ".ogg", ".oga", ".webm")
        ):
            return filepath

    return None


def get_image_filepaths(input_folder: str) -> List[str]:
    images = []
    if not os.path.exists(input_folder):
        return images

    valid_extensions = (".jpg", ".jpeg", ".png", ".webp", ".gif")
    for filename in sorted(os.listdir(input_folder)):
        filepath = os.path.join(input_folder, filename)
        if not os.path.isfile(filepath) or filename.startswith("."):
            continue

        mime_type, _ = mimetypes.guess_type(filepath)
        mime_type = mime_type or ""
        if mime_type.startswith("image/") or filename.lower().endswith(valid_extensions):
            images.append(filepath)

    return images
