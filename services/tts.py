"""Cường — chữ → mp3.

Thứ tự: file mp3 đã pre-generate trong audio/ → edge-tts → gTTS → None (UI chỉ hiện chữ).
Tên file: audio/<poi_id>_<lang>.mp3 — pre-generate cho các POI trong kịch bản demo.
"""
import os

from config import AUDIO_DIR

VOICES = {
    "vi": "vi-VN-HoaiMyNeural",
    "en": "en-US-AriaNeural",
    "ko": "ko-KR-SunHiNeural",
    "ja": "ja-JP-NanamiNeural",
    "zh": "zh-CN-XiaoxiaoNeural",
}
GTTS_LANG = {"vi": "vi", "en": "en", "ko": "ko", "ja": "ja", "zh": "zh-CN"}


def audio_path(poi_id: str, lang: str) -> str:
    return os.path.join(AUDIO_DIR, "%s_%s.mp3" % (poi_id, lang))


def synthesize(text: str, lang: str, out_path: str) -> str | None:
    """Trả đường dẫn mp3, hoặc None nếu cả hai cách đều lỗi."""
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    try:
        import asyncio
        import edge_tts
        asyncio.run(edge_tts.Communicate(text, VOICES.get(lang, VOICES["en"])).save(out_path))
        return out_path
    except Exception:
        pass
    try:
        from gtts import gTTS
        gTTS(text, lang=GTTS_LANG.get(lang, "en")).save(out_path)
        return out_path
    except Exception:
        return None


def get_or_create_audio(poi_id: str, lang: str, text: str) -> str | None:
    path = audio_path(poi_id, lang)
    if os.path.exists(path):
        return path
    return synthesize(text, lang, path)
