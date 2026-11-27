"""Offline regression tests: python -m unittest discover -s tests -v."""
import asyncio
import datetime as dt
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import URLError

from services import tts, weather

MP3 = b"ID3" + b"\0" * 200


class WeatherTests(unittest.TestCase):
    def setUp(self):
        weather._cache.clear()
        self.date = dt.datetime.now(weather.TIMEZONE).date().isoformat()
        self.env = patch.dict(os.environ, {"WEATHER_MODE": "real"})
        self.env.start()
        self.addCleanup(self.env.stop)

    def payload(self):
        return {"hourly": {"time": [f"{self.date}T{h:02d}:00" for h in range(24)],
                           "precipitation_probability": [10]*13 + [70]*11, "temperature_2m": list(range(24))}}

    def response(self, payload):
        return io.StringIO(json.dumps(payload))

    def test_real_values_and_cache_are_not_mutable(self):
        with patch.object(weather, "urlopen", return_value=self.response(self.payload())) as request:
            first = weather.get_weather(self.date, 21, 105)
            self.assertEqual(first["temp_max"], 23)
            self.assertTrue(first["is_rainy"])
            self.assertFalse(first["mock"])
            self.assertEqual(first["status"], "ok")
            first["rain_prob_by_hour"].clear()
            cached = weather.get_weather(self.date, 21, 105)
            self.assertEqual(len(cached["rain_prob_by_hour"]), 24)
            self.assertTrue(cached["cached"])
            request.assert_called_once()

    def test_missing_probability_does_not_mean_no_rain(self):
        payload = self.payload()
        payload["hourly"]["precipitation_probability"] = [None]*24
        with patch.object(weather, "urlopen", return_value=self.response(payload)):
            result = weather.get_weather(self.date, 21, 105)
        self.assertIsNone(result["is_rainy"])
        self.assertEqual(result["status"], "partial")

    def test_outage_never_fabricates_weather(self):
        with patch.object(weather, "urlopen", side_effect=URLError("offline")):
            result = weather.get_weather(self.date, 21, 105)
        self.assertIsNone(result["temp_max"])
        self.assertIsNone(result["is_rainy"])
        self.assertFalse(result["mock"])
        self.assertEqual(result["status"], "unavailable")

    def test_mock_is_explicit_and_needs_no_network(self):
        with patch.dict(os.environ, {"WEATHER_MODE": "mock"}), patch.object(weather, "urlopen") as request:
            self.assertTrue(weather.get_weather(self.date, 21, 105)["mock"])
            request.assert_not_called()

    def test_bad_input_and_outside_forecast_window(self):
        with patch.object(weather, "urlopen") as request:
            self.assertEqual(weather.get_weather("invalid", 21, 105)["error_code"], "invalid_input")
            self.assertEqual(weather.get_weather(self.date, 200, 105)["error_code"], "invalid_input")
            self.assertEqual(weather.get_weather("2099-01-01", 21, 105)["error_code"], "out_of_range")
            request.assert_not_called()

    def test_bad_arrays_and_null_temperature(self):
        with patch.object(weather, "urlopen", return_value=self.response({"hourly": {}})):
            self.assertEqual(weather.get_weather(self.date, 21, 105)["status"], "unavailable")
        payload = self.payload()
        payload["hourly"]["temperature_2m"] = [None]*24
        with patch.object(weather, "urlopen", return_value=self.response(payload)):
            result = weather.get_weather(self.date, 21, 105)
        self.assertIsNone(result["temp_max"])
        self.assertTrue(result["is_rainy"])


class TTSTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.env = patch.object(tts, "AUDIO_DIR", self.directory.name)
        self.env.start()
        self.addCleanup(self.env.stop)

    def save(self, text, lang, path):
        Path(path).write_bytes(MP3)

    def test_five_languages_and_fallback(self):
        for lang in tts.VOICES:
            with patch.object(tts, "_run_edge", side_effect=RuntimeError), patch.object(tts, "_gtts_save", side_effect=self.save):
                result = tts.get_audio_result("poi", lang, "Reviewed narration")
                self.assertEqual(result["tts_provider"], "gtts")
                self.assertTrue(tts.valid_audio(result["audio_path"]))

    def test_no_stale_audio_after_text_changes(self):
        with patch.object(tts, "_run_edge", side_effect=self.save) as request:
            first = tts.get_audio_result("poi", "vi", "First narration")
            cached = tts.get_audio_result("poi", "vi", "First narration")
            changed = tts.get_audio_result("poi", "vi", "Changed narration")
        self.assertEqual(cached["tts_status"], "cached")
        self.assertEqual(request.call_count, 2)
        self.assertNotEqual(first["audio_version"], changed["audio_version"])

    def test_failed_provider_does_not_publish_partial_file(self):
        path = tts.audio_path("poi", "vi")
        Path(path).write_bytes(MP3)
        def broken(text, lang, temporary):
            Path(temporary).write_bytes(b"partial")
        with patch.object(tts, "_run_edge", side_effect=broken), patch.object(tts, "_gtts_save", side_effect=broken):
            result = tts.synthesize_result("Text", "vi", path)
        self.assertIsNone(result["audio_path"])
        self.assertEqual(Path(path).read_bytes(), MP3)
        self.assertEqual(len(list(Path(self.directory.name).glob("*.mp3"))), 1)

    def test_invalid_language_and_path_rejected(self):
        for poi, lang in (("../secret", "vi"), ("poi", "fr")):
            with self.assertRaises(ValueError):
                tts.audio_path(poi, lang)

    def test_prepared_requires_approval_and_matching_context(self):
        with patch.object(tts, "_run_edge", side_effect=self.save):
            result = tts.get_audio_result("poi", "en", "Approved narration")
        path = result["audio_path"]
        self.assertIsNone(tts.load_prepared_audio("poi", "en"))
        metadata = json.loads(Path(path).with_suffix(".json").read_text(encoding="utf-8"))
        metadata.update(approved=True, prepared=True, context_sha256=tts.text_hash("context"))
        tts.write_metadata(path, metadata)
        self.assertEqual(tts.load_prepared_audio("poi", "en", "context")["source"], "prepared")
        self.assertIsNone(tts.load_prepared_audio("poi", "en", "new context"))
        Path(path).write_bytes(MP3 + b"tampered")
        self.assertIsNone(tts.load_prepared_audio("poi", "en", "context"))

    def test_sync_api_also_works_inside_running_event_loop(self):
        async def save(text, lang, path):
            self.save(text, lang, path)
        async def exercise():
            with patch.object(tts, "_edge_save", side_effect=save):
                return tts.synthesize_result("Text", "en", tts.audio_path("poi", "en"))
        self.assertEqual(asyncio.run(exercise())["tts_provider"], "edge-tts")


if __name__ == "__main__":
    unittest.main()
