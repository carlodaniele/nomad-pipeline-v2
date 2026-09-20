import json
from pathlib import Path
from typing import Any, Dict, Optional, Union


DEFAULT_SETTINGS_PATH = Path(__file__).with_name("settings.json")
DEFAULT_SETTINGS: Dict[str, Any] = {
    "language": "en-US",
    "tone": "neutral",
    "target_length": "medium",
    "proper_noun_hints": ["Astro"],
    "constraints": ["Use clear headings and short paragraphs."],
}


def _coerce_settings(raw: Any) -> Dict[str, Any]:
    if not isinstance(raw, dict):
        return dict(DEFAULT_SETTINGS)

    normalized = dict(DEFAULT_SETTINGS)
    for key, default_value in DEFAULT_SETTINGS.items():
        if key in raw:
            normalized[key] = raw[key]
    return normalized


def load_astro_settings(path: Optional[Union[str, Path]] = None) -> Dict[str, Any]:
    settings_path = Path(path) if path is not None else DEFAULT_SETTINGS_PATH
    if not settings_path.exists():
        return dict(DEFAULT_SETTINGS)

    try:
        with open(settings_path, "r", encoding="utf-8") as fh:
            raw_settings = json.load(fh)
    except (json.JSONDecodeError, OSError):
        return dict(DEFAULT_SETTINGS)

    return _coerce_settings(raw_settings)
