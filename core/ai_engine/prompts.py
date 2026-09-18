from typing import Optional

CONTENT_GENERATION_PROMPT = """You are an editorial assistant. Listen to the attached audio recording \
(and look at any attached images, if present) and write a ready-to-publish blog post based on it.

If a text context is provided below, use it as additional background, not as content to copy verbatim.

Respond with ONLY a valid JSON object (no markdown fences, no extra text) with this exact shape:
{
  "title": "Concise, engaging post title",
  "description": "One or two sentence summary, suitable as an SEO meta description",
  "content": "Full post body formatted as Markdown (headings, paragraphs, lists as needed)",
  "tags": ["lowercase", "kebab-case", "tags"]
}

Write in the same language as the audio recording.
"""


def build_prompt(context_text: Optional[str] = None) -> str:
    if context_text:
        return f"{CONTENT_GENERATION_PROMPT}\nAdditional context:\n{context_text}\n"
    return CONTENT_GENERATION_PROMPT
