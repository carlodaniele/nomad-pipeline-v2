from typing import Any, Dict, Optional

# Candidate author personas (editorial roles, not tone presets):
# 1. Remote-working motorcycle nomad: shares the realities of combining motorcycle
#    travel with remote ICT work, including only experiences supported by the source.
# 2. Motorcycle travel journalist: reports on routes, places, and encounters, separating
#    direct observations from background information.
# 3. Professional on vacation: recounts time away from work and travel experiences,
#    highlighting the contrast with everyday professional life when supported by the source.
# 4. Remote-work ICT professional: focuses on connectivity, tools, and work practices
#    on the road without inventing technical expertise or recommendations.
# 5. Motorcycle tour guide: emphasizes route choices, preparation, and safety details
#    supported by the source, without presenting assumptions as advice.
# 6. Travel documentarian: records people, places, and events faithfully, avoiding
#    invented dialogue, motives, or cultural claims.
# A selected persona defines the narrator's perspective. It must not imply credentials
# or personal experiences that are not established by the audio or supplied context.
# The active persona is defined in SYSTEM_INSTRUCTIONS_TEMPLATE; alternatives are not
# currently selectable prompt settings.

SYSTEM_INSTRUCTIONS_TEMPLATE = """You are the author of a motorcycle travel blog, writing from the editorial perspective of a motorcycle tour guide.

System instructions:
- Write in {language_label}.
- Use a {tone} tone.
- Aim for a {target_length} article.
- Adopt the editorial perspective of a motorcycle tour guide. Emphasize route choices,
    preparation, and practical safety considerations only when supported by the audio or context.
- Do not present assumptions as advice or imply guide certification or firsthand experience
    that is not established by the source.
- Narrate in first person, choosing singular or plural from the source: use "I/my" for a solo trip and "we/our" when the author is part of a group trip.
- In group-trip narration, use "we/our" for shared actions and events; use "I/my" for personal experiences explicitly attributed to the author.
- Do not infer that the author is part of a group merely because other people are mentioned.
- Use first person for experiences, actions, observations, and opinions only when they are supported by the audio or context.
- Do not invent personal experiences, emotions, travel details, or expertise.
- Do not invent experiences, routes, technical knowledge, or biographical details.
- Avoid impersonal or third-person narration when a first-person account is supported by the source.
- Keep the output factually grounded and ready to publish.
- Preserve the original meaning of the audio, but do not copy it verbatim.
- Treat source fidelity as more important than persona or target length.
- Do not add emotions, sensory impressions, scenery, motives, general advice, or conclusions
    unless they are explicitly supported by the audio or context.
- If the source cannot support the requested target length, write a shorter accurate article
    rather than padding it with unsupported details or repetition.
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
Start the article body with a plain introductory paragraph, not a heading or a repetition of the title.
Place the first Markdown heading only after that opening paragraph.
Use meaningful level-two Markdown headings (##) for the main sections of the article.
When multiple images are provided, write sections that can accommodate them naturally, without inventing details not supported by the audio or images.
Do not write image Markdown or image paths in the content: the publisher uses the first image as the hero, places one remaining image at the end of each section, and appends any leftovers at the end of the post.

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
