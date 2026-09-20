import math
import os
import unittest
import wave

from adapters.astro.media_utils import get_audio_filepath


class AstroAudioFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture_dir = os.path.join(os.path.dirname(__file__), "fixtures")
        os.makedirs(cls.fixture_dir, exist_ok=True)
        cls.audio_path = os.path.join(cls.fixture_dir, "sample_audio.wav")

        if not os.path.exists(cls.audio_path):
            sample_rate = 22050
            duration_seconds = 1.0
            total_frames = int(sample_rate * duration_seconds)
            amplitude = 0.5

            with wave.open(cls.audio_path, "wb") as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(sample_rate)
                frames = []
                for index in range(total_frames):
                    value = int(amplitude * 32767 * math.sin(2 * math.pi * 440 * index / sample_rate))
                    frames.append(value.to_bytes(2, byteorder="little", signed=True))
                wav_file.writeframes(b"".join(frames))

    def test_audio_fixture_is_detected_as_audio(self):
        detected = get_audio_filepath(self.fixture_dir)
        self.assertIsNotNone(detected)
        self.assertTrue(detected.endswith("sample_audio.wav"))


if __name__ == "__main__":
    unittest.main()
