import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app_config import AppSettings, load_settings, save_settings, validate_settings


class AppSettingsTests(unittest.TestCase):
    def test_settings_round_trip(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "settings.json"
            with patch("app_config._SETTINGS_PATH", path):
                settings = AppSettings(
                    llm_model="example-model",
                    stt_language="fi",
                    turn_speed=72,
                )
                save_settings(settings)
                loaded = load_settings()

        self.assertEqual(loaded.llm_model, "example-model")
        self.assertEqual(loaded.stt_language, "fi")
        self.assertEqual(loaded.turn_speed, 72)

    def test_rejects_unsafe_provider_url_and_voice_path(self):
        with self.assertRaises(ValueError):
            validate_settings(AppSettings(llm_base_url="file:///not-a-provider"))

        with self.assertRaises(ValueError):
            validate_settings(AppSettings(tts_voice="../outside.wav"))

    def test_openai_compatible_provider_requires_a_base_url(self):
        with self.assertRaises(ValueError):
            validate_settings(AppSettings(llm_provider="openai_compatible"))

        settings = validate_settings(
            AppSettings(
                llm_provider="openai_compatible",
                llm_base_url="http://127.0.0.1:8080/v1",
            )
        )
        self.assertEqual(settings.llm_base_url, "http://127.0.0.1:8080/v1")


if __name__ == "__main__":
    unittest.main()
