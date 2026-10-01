import json
import os
import tempfile
import unittest
from unittest.mock import patch


class TelegramJourneyStagingTests(unittest.TestCase):
    def test_audio_snapshots_journey_at_poll_time(self):
        with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "test"}):
            import telegram_poll

        update = {
            "update_id": 1,
            "message": {"chat": {"id": 123}, "message_id": 42, "voice": {"file_id": "audio"}},
        }
        with tempfile.TemporaryDirectory() as input_dir, patch.dict(
            os.environ, {"JOURNEY_ID": " 2026-spain-morocco "}
        ), patch.object(telegram_poll, "INPUT_FOLDER", input_dir), patch.object(
            telegram_poll, "STATE_FILE", os.path.join(input_dir, "offset")
        ), patch.object(telegram_poll, "ensure_polling_mode"), patch.object(
            telegram_poll, "get_updates", return_value=[update]
        ), patch.object(telegram_poll, "download_telegram_file") as download:
            download.side_effect = lambda file_id, destination: open(destination, "wb").close()
            telegram_poll.main()

            metadata_path = os.path.join(input_dir, "123_42.oga.json")
            with patch.dict(os.environ, {"JOURNEY_ID": "2026-another-trip"}):
                with open(metadata_path, "r", encoding="utf-8") as metadata_file:
                    self.assertEqual(json.load(metadata_file), {"journey_id": "2026-spain-morocco"})

    def test_unset_journey_snapshots_empty_value(self):
        with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "test"}):
            import telegram_poll

        update = {
            "update_id": 1,
            "message": {"chat": {"id": 123}, "message_id": 42, "voice": {"file_id": "audio"}},
        }
        for value in (None, "  "):
            with self.subTest(value=value), tempfile.TemporaryDirectory() as input_dir, patch.dict(
                os.environ, {} if value is None else {"JOURNEY_ID": value}, clear=value is None
            ), patch.object(telegram_poll, "INPUT_FOLDER", input_dir), patch.object(
                telegram_poll, "STATE_FILE", os.path.join(input_dir, "offset")
            ), patch.object(telegram_poll, "ensure_polling_mode"), patch.object(
                telegram_poll, "get_updates", return_value=[update]
            ), patch.object(telegram_poll, "download_telegram_file") as download:
                download.side_effect = lambda file_id, destination: open(destination, "wb").close()
                telegram_poll.main()
                with open(os.path.join(input_dir, "123_42.oga.json"), "r", encoding="utf-8") as metadata_file:
                    self.assertEqual(json.load(metadata_file), {"journey_id": ""})


if __name__ == "__main__":
    unittest.main()