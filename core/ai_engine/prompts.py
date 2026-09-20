from typing import Any, Dict, Optional

SYSTEM_INSTRUCTIONS_TEMPLATE = """You are an editorial assistant for a content pipeline.

System instructions:
- Write in {language_label}.
- Use a {tone} tone.
- Aim for a {target_length} article.
- Keep the output factually grounded and ready to publish.
- Preserve the original meaning of the audio, but do not copy it verbatim.
- Use the following proper noun hints exactly as needed: {proper_noun_hints}.
- Apply these additional editorial constraints: {constraints}.
- Produce a valid JSON object with this exact shape:
{{
  "title": "Concise, engaging post title",
  "description": "One or two sentence summary, suitable as an SEO meta description",
  "content": "Full post body formatted as Markdown (headings, paragraphs, lists as needed)",
  "tags": ["lowercase", "kebab-case", "tags"]
}}
- Do not wrap the JSON in markdown fences or add extra commentary.
"""

MAIN_PROMPT_TEMPLATE = """Create a blog post from the attached audio and any provided images.

If a transcript is available, use it as the primary source.
If extra context is provided, use it as supporting background only.
Do not copy the context verbatim.

Transcript:
{transcript}

Additional context:
{context_text}
"""


def _normalize_language_label(language: str) -> str:
    if language == "auto":
        return "the same language as the audio"
    if language == "en-US":
        return "English (United States)"
    if language == "en-GB":
        return "English (United Kingdom)"
    if language == "it-IT":
        return "Italian"
    if language == "de-DE":
        return "German"
    if language == "fr-FR":
        return "French"
    if language == "es-ES":
        return "Spanish"
    if language == "nl-NL":
        return "Dutch"
    if language == "pl-PL":
        return "Polish"
    return language


def build_system_instructions(settings: Optional[Dict[str, Any]] = None) -> str:
    config = settings or {}
    language = str(config.get("language", "auto"))
    tone = str(config.get("tone", "neutral"))
    target_length = str(config.get("target_length", "medium"))
    proper_noun_hints = config.get("proper_noun_hints") or []
    constraints = config.get("constraints") or []

    if not isinstance(proper_noun_hints, list):
        proper_noun_hints = [str(proper_noun_hints)]
    if not isinstance(constraints, list):
        constraints = [str(constraints)]

    hints = ", ".join(str(item) for item in proper_noun_hints) if proper_noun_hints else "none"
    rules = "; ".join(str(item) for item in constraints) if constraints else "none"

    return SYSTEM_INSTRUCTIONS_TEMPLATE.format(
        language_label=_normalize_language_label(language),
        tone=tone,
        target_length=target_length,
        proper_noun_hints=hints,
        constraints=rules,
    )


def build_main_prompt(transcript: str = "", context_text: Optional[str] = None) -> str:
    rendered_context = context_text or "None provided."
    return MAIN_PROMPT_TEMPLATE.format(
        transcript=transcript or "No transcript was provided; rely on the audio and any attached images.",
        context_text=rendered_context,
    )


def build_prompt(context_text: Optional[str] = None, transcript: str = "", settings: Optional[Dict[str, Any]] = None) -> str:
    system_instructions = build_system_instructions(settings)
    main_prompt = build_main_prompt(transcript=transcript, context_text=context_text)
    return f"{system_instructions}\n\n{main_prompt}"
