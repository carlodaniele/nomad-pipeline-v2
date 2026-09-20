import unittest

from adapters.astro.settings_loader import load_astro_settings
from core.ai_engine.prompts import build_main_prompt, build_prompt, build_system_instructions


class AstroPromptSettingsTests(unittest.TestCase):
    def test_settings_file_loads_defaults(self):
        settings = load_astro_settings()
        self.assertEqual(settings["language"], "en-US")
        self.assertEqual(settings["tone"], "neutral")
        self.assertIn("Astro", settings["proper_noun_hints"])

    def test_system_instructions_include_user_config(self):
        settings = load_astro_settings()
        system = build_system_instructions(settings)
        self.assertIn("Write in English (United States)", system)
        self.assertIn("neutral tone", system.lower())
        self.assertIn("Astro", system)
        self.assertIn("Use clear headings and short paragraphs.", system)

    def test_main_prompt_keeps_runtime_work(self):
        main = build_main_prompt(context_text="Extra context", transcript="Transcribed text")
        self.assertIn("Extra context", main)
        self.assertIn("Transcribed text", main)
        self.assertNotIn("Write in English (United States)", main)

    def test_final_prompt_keeps_system_and_runtime_separated(self):
        settings = load_astro_settings()
        prompt = build_prompt(
            context_text="Extra context",
            transcript="Transcribed text",
            settings=settings,
        )

        self.assertIn("System instructions:", prompt)
        self.assertIn("Write in English (United States)", prompt)
        self.assertIn("Transcribed text", prompt)
        self.assertIn("Extra context", prompt)

        main = build_main_prompt(transcript="Transcribed text", context_text="Extra context")
        self.assertNotIn("Write in English (United States)", main)
        self.assertNotIn("System instructions:", main)


if __name__ == "__main__":
    unittest.main()
