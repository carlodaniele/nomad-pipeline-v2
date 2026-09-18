import os
from typing import List, Optional

from google import genai
from google.genai import types

from .base import AIProvider, ContentResult
from .prompts import build_prompt


class GeminiProvider(AIProvider):
    def __init__(self) -> None:
        api_key = (os.getenv("GEMINI_API_KEY", "") or "").strip()
        if not api_key:
            raise ValueError("GEMINI_API_KEY is not configured in the environment variables.")

        self._model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        self._client = genai.Client(api_key=api_key)

    def generate_content(
        self,
        audio_path: str,
        image_paths: Optional[List[str]] = None,
        context_text: Optional[str] = None,
    ) -> ContentResult:
        contents = [self._client.files.upload(file=audio_path)]
        for image_path in image_paths or []:
            contents.append(self._client.files.upload(file=image_path))
        contents.append(build_prompt(context_text))

        response = self._client.models.generate_content(
            model=self._model,
            contents=contents,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=ContentResult,
            ),
        )

        parsed = response.parsed
        if isinstance(parsed, ContentResult):
            return parsed
        return ContentResult.model_validate(parsed)
