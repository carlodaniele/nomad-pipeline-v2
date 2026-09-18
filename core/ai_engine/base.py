from abc import ABC, abstractmethod
from typing import List, Optional

from pydantic import BaseModel


class ContentResult(BaseModel):
    """CMS-agnostic output of an AI content generation run."""

    title: str
    description: str
    content: str
    tags: List[str] = []


class AIProvider(ABC):
    """Common interface every AI provider (Gemini, etc.) must implement."""

    @abstractmethod
    def generate_content(
        self,
        audio_path: str,
        image_paths: Optional[List[str]] = None,
        context_text: Optional[str] = None,
    ) -> ContentResult:
        """Transcribe the audio and return structured blog content."""
        raise NotImplementedError
