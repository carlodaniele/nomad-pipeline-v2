import unittest
from unittest.mock import Mock, patch

from core.ai_engine.gemini_client import GeminiProvider


class GeminiProviderPromptRequestTests(unittest.TestCase):
    @patch("core.ai_engine.gemini_client.genai.Client")
    def test_generate_content_uses_settings_in_system_instruction(self, mock_client_cls):
        mock_client = Mock()
        mock_client.files.upload.side_effect = ["uploaded_audio", "uploaded_image"]
        mock_response = Mock()
        mock_response.parsed = {
            "title": "Example title",
            "description": "Example description",
            "content": "Example content",
            "tags": ["example"],
        }
        mock_client.models.generate_content.return_value = mock_response
        mock_client_cls.return_value = mock_client

        provider = GeminiProvider.__new__(GeminiProvider)
        provider._model = "gemini-2.5-flash"
        provider._client = mock_client

        with patch("adapters.astro.settings_loader.load_astro_settings") as mock_load_settings:
            mock_load_settings.return_value = {
                "language": "en-US",
                "tone": "neutral",
                "target_length": "medium",
                "proper_noun_hints": ["Astro"],
                "constraints": ["Use clear headings and short paragraphs."],
            }

            result = provider.generate_content(
                audio_path="audio.mp3",
                image_paths=["image.jpg"],
                context_text="Extra context",
                transcript="Transcribed text",
            )

        self.assertEqual(result.title, "Example title")
        config = mock_client.models.generate_content.call_args.kwargs["config"]
        self.assertIn("Write in English (United States)", config.system_instruction)
        self.assertIn("neutral tone", config.system_instruction.lower())
        self.assertIn("Astro", config.system_instruction)

        contents = mock_client.models.generate_content.call_args.kwargs["contents"]
        self.assertEqual(contents[0], "uploaded_audio")
        self.assertEqual(contents[1], "uploaded_image")
        self.assertIn("Transcribed text", contents[2])
        self.assertIn("Extra context", contents[2])


if __name__ == "__main__":
    unittest.main()
