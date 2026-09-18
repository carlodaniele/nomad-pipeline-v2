import os
from typing import List, Optional

from .base import AIProvider, ContentResult


def _get_provider() -> AIProvider:
    provider_name = (os.getenv("AI_PROVIDER", "gemini") or "gemini").strip().lower()

    if provider_name == "gemini":
        from .gemini_client import GeminiProvider

        return GeminiProvider()

    raise ValueError(f"Unknown AI_PROVIDER: {provider_name}")


def generate_content(
    audio_path: str,
    image_paths: Optional[List[str]] = None,
    context_text: Optional[str] = None,
) -> ContentResult:
    provider = _get_provider()
    return provider.generate_content(audio_path, image_paths, context_text)
