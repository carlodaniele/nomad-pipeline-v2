import os
import shutil
import tempfile
import unittest
from unittest.mock import patch

from core.ai_engine.base import ContentResult


class AstroAdapterRunTests(unittest.TestCase):
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
                        content="## Intro\n\nThis is example content.",
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
