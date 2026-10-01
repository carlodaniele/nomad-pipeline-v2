import json
import os
import shutil
import tempfile
import unittest
from unittest.mock import patch

from core.ai_engine.base import ContentResult
from adapters.astro.content_builder import build_markdown


class AstroAdapterRunTests(unittest.TestCase):
    def test_extra_images_follow_sections_then_overflow_at_end(self):
        result = ContentResult(
            title="Trip", description="Description", tags=[],
            content="Introduction.\n\n## First\n\nFirst text.\n\n### Details\n\nMore text.\n\n## Second\n\nSecond text.",
        )
        markdown = build_markdown(
            result, hero_image="hero.jpg", extra_images=["one.jpg", "two.jpg", "three.jpg"]
        )
        self.assertIn("heroImage: \"hero.jpg\"", markdown)
        self.assertIn("More text.\n\n![Trip](one.jpg)\n\n## Second", markdown)
        self.assertTrue(markdown.endswith("Second text.\n\n![Trip](two.jpg)\n\n![Trip](three.jpg)\n"))
        self.assertTrue(build_markdown(result, extra_images=["one.jpg"]).endswith(
            "More text.\n\n![Trip](one.jpg)\n\n## Second\n\nSecond text.\n"
        ))

        for first_heading in ("# Trip", "## First", "  "):
            with self.subTest(first_heading=first_heading):
                section_first = ContentResult(
                    title="Trip", description="Description", tags=[],
                    content=f"{first_heading}\n\nText." if first_heading.strip() else first_heading,
                )
                with self.assertRaisesRegex(ValueError, "introductory paragraph"):
                    build_markdown(section_first, extra_images=["one.jpg"])

        no_sections = ContentResult(title="Trip", description="Description", tags=[], content="Just text.")
        self.assertTrue(build_markdown(no_sections, extra_images=["one.jpg"]).endswith(
            "Just text.\n\n![Trip](one.jpg)\n"
        ))

    def test_journey_is_snapshot_and_validated_before_generation(self):
        from adapters.astro.adapter import run

        with tempfile.TemporaryDirectory() as tmp_dir:
            input_dir = os.path.join(tmp_dir, "media-input")
            journeys_dir = os.path.join(tmp_dir, "astro-site", "src", "content", "journeys")
            os.makedirs(input_dir)
            os.makedirs(journeys_dir)
            audio_path = os.path.join(input_dir, "recording.oga")
            with open(audio_path, "wb") as audio_file:
                audio_file.write(b"audio")
            with open(os.path.join(journeys_dir, "2026-spain-morocco.md"), "w") as journey_file:
                journey_file.write("---\ntitle: Trip\n---\n")

            content = ContentResult(
                title="Test post", description="Description", content="Body", tags=[]
            )
            environment = {
                "GH_INPUT_FOLDER": input_dir,
                "ASTRO_JOURNEYS_DIR": journeys_dir,
                "ASTRO_CONTENT_DIR": os.path.join(tmp_dir, "content"),
                "ASTRO_ASSETS_DIR": os.path.join(tmp_dir, "assets"),
                "JOURNEY_ID": "2026-some-new-trip",
            }
            with patch.dict(os.environ, environment), patch(
                "adapters.astro.adapter.generate_content", return_value=content
            ) as generate:
                for value in (None, "", "   ", "2026-spain-morocco"):
                    with self.subTest(value=value):
                        if value is None:
                            if os.path.exists(f"{audio_path}.json"):
                                os.remove(f"{audio_path}.json")
                        else:
                            with open(f"{audio_path}.json", "w", encoding="utf-8") as metadata_file:
                                json.dump({"journey_id": value}, metadata_file)
                        post = run()
                        with open(post["file_path"], "r", encoding="utf-8") as post_file:
                            markdown = post_file.read()
                        self.assertEqual("journey:" in markdown, value == "2026-spain-morocco")
                        if value == "2026-spain-morocco":
                            self.assertIn('journey: "2026-spain-morocco"', markdown)

                for value, exception in (
                    ("2026-unknown", ValueError),
                    ("../2026-spain-morocco", ValueError),
                ):
                    with self.subTest(value=value):
                        with open(f"{audio_path}.json", "w", encoding="utf-8") as metadata_file:
                            json.dump({"journey_id": value}, metadata_file)
                        before = generate.call_count
                        with self.assertRaises(exception):
                            run()
                        self.assertEqual(generate.call_count, before)

                os.remove(os.path.join(journeys_dir, "2026-spain-morocco.md"))
                with open(f"{audio_path}.json", "w", encoding="utf-8") as metadata_file:
                    json.dump({"journey_id": "2026-spain-morocco"}, metadata_file)
                before = generate.call_count
                with self.assertRaises(ValueError):
                    run()
                os.rmdir(journeys_dir)
                with self.assertRaises(FileNotFoundError):
                    run()
                self.assertEqual(generate.call_count, before)

    def test_run_generates_markdown_and_assets_from_real_fixture(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            input_dir = os.path.join(tmp_dir, "media-input")
            content_dir = os.path.join(tmp_dir, "content", "blog")
            assets_dir = os.path.join(tmp_dir, "public", "images", "blog")
            os.makedirs(input_dir, exist_ok=True)

            fixture_dir = os.path.join(os.path.dirname(__file__), "fixtures")
            source_audio = os.path.join(fixture_dir, "sample_audio.wav")
            source_image = os.path.join(fixture_dir, "sample_image.png")

            if not os.path.exists(source_audio):
                raise FileNotFoundError("Missing sample audio fixture for Astro adapter test.")

            shutil.copy2(source_audio, os.path.join(input_dir, "sample_audio.wav"))

            if not os.path.exists(source_image):
                with open(source_image, "wb") as fh:
                    fh.write(b"\x89PNG\r\n\x1a\n")
            shutil.copy2(source_image, os.path.join(input_dir, "sample_image.png"))

            with patch.dict(
                os.environ,
                {
                    "GH_INPUT_FOLDER": input_dir,
                    "ASTRO_CONTENT_DIR": content_dir,
                    "ASTRO_ASSETS_DIR": assets_dir,
                    "ASTRO_ASSET_URL_PREFIX": "../../assets/blog",
                },
                clear=False,
            ):
                with patch("adapters.astro.adapter.generate_content") as mock_generate_content:
                    mock_generate_content.return_value = ContentResult(
                        title="Example Astro Post",
                        description="Example description for the generated article.",
                        content="Introduction.\n\n## Intro\n\nThis is example content.",
                        tags=["astro", "audio"],
                    )

                    from adapters.astro.adapter import run

                    result = run()

            self.assertEqual(result["status"], "completed")
            self.assertTrue(any(name.endswith(".md") for name in os.listdir(content_dir)))
            self.assertTrue(any(name.endswith(".png") for name in os.listdir(assets_dir)))

            markdown_files = os.listdir(content_dir)
            markdown_path = os.path.join(content_dir, markdown_files[0])
            with open(markdown_path, "r", encoding="utf-8") as fh:
                markdown = fh.read()

            self.assertIn("title: \"Example Astro Post\"", markdown)
            self.assertIn("heroImage", markdown)
            self.assertIn("This is example content.", markdown)


if __name__ == "__main__":
    unittest.main()
