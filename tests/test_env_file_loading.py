import os
import unittest


class EnvFileLoadingTests(unittest.TestCase):
    def test_project_dotenv_is_loaded_when_importing_astro_adapter(self):
        import importlib

        import adapters.astro.adapter as astro_adapter

        importlib.reload(astro_adapter)
        self.assertTrue(os.getenv("GEMINI_API_KEY", "").strip())


if __name__ == "__main__":
    unittest.main()
