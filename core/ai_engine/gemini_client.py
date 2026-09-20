import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

from .base import AIProvider, ContentResult
from .prompts import build_main_prompt, build_system_instructions


class GeminiProvider(AIProvider):
    def __init__(self) -> None:
        api_key = (os.getenv("GEMINI_API_KEY", "") or "").strip()
        if not api_key:
            raise ValueError("GEMINI_API_KEY is not configured in the environment variables.")

        self._model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        self._client = genai.Client(api_key=api_key)

    def _load_settings(self) -> Dict[str, Any]:
        try:
            from adapters.astro.settings_loader import load_astro_settings

            return load_astro_settings()
        except Exception:
            return {}

    def generate_content(
        self,
        audio_path: str,
        image_paths: Optional[List[str]] = None,
        context_text: Optional[str] = None,
        transcript: str = "",
    ) -> ContentResult:
        settings = self._load_settings()
        system_instruction = build_system_instructions(settings)
        main_prompt = build_main_prompt(transcript=transcript, context_text=context_text)

        contents = [self._client.files.upload(file=audio_path)]
        for image_path in image_paths or []:
            contents.append(self._client.files.upload(file=image_path))
        contents.append(main_prompt)

        response = self._client.models.generate_content(
            model=self._model,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                response_schema=ContentResult,
            ),
        )

        parsed = response.parsed
        if isinstance(parsed, ContentResult):
            return parsed
        return ContentResult.model_validate(parsed)
