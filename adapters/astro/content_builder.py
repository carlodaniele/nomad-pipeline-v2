import re
from datetime import date
from typing import List, Optional

from core.ai_engine import ContentResult


def slugify(text: str) -> str:
    slug = text.strip().lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-") or "post"


def _yaml_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def build_frontmatter(result: ContentResult, hero_image: Optional[str] = None) -> str:
    lines = ["---"]
    lines.append(f'title: "{_yaml_escape(result.title)}"')
    lines.append(f'description: "{_yaml_escape(result.description)}"')
    lines.append(f"pubDate: {date.today().isoformat()}")

    if result.tags:
        tags_yaml = ", ".join(f'"{_yaml_escape(tag)}"' for tag in result.tags)
        lines.append(f"tags: [{tags_yaml}]")

    if hero_image:
        lines.append(f'heroImage: "{hero_image}"')

    lines.append("---")
    return "\n".join(lines)


def build_markdown(
    result: ContentResult,
    hero_image: Optional[str] = None,
    extra_images: Optional[List[str]] = None,
) -> str:
    frontmatter = build_frontmatter(result, hero_image)
    body = result.content.strip()

    for image_path in extra_images or []:
        body += f'\n\n![{result.title}]({image_path})'

    return f"{frontmatter}\n\n{body}\n"


def build_filename(title: str) -> str:
    return f"{date.today().isoformat()}-{slugify(title)}.md"
