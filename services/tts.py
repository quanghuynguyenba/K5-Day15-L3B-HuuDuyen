"""Five-language TTS with bounded providers, atomic files and content-aware cache."""
import asyncio
from concurrent.futures import ThreadPoolExecutor
import datetime as dt
import hashlib
import json
import logging
import os
from pathlib import Path
import re
import tempfile
import threading

from config import AUDIO_DIR

logger = logging.getLogger(__name__)
VOICES = {"vi": "vi-VN-HoaiMyNeural", "en": "en-US-AriaNeural", "ko": "ko-KR-SunHiNeural",
          "ja": "ja-JP-NanamiNeural", "zh": "zh-CN-XiaoxiaoNeural"}
GTTS_LANG = {"vi": "vi", "en": "en", "ko": "ko", "ja": "ja", "zh": "zh-CN"}
_locks = {}
_guard = threading.Lock()


def text_hash(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def validate_language(lang):
    if lang not in VOICES:
        raise ValueError("Ngôn ngữ phải là vi, en, ko, ja hoặc zh.")


def audio_path(poi_id: str, lang: str) -> str:
    validate_language(lang)
    if not isinstance(poi_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", poi_id):
        raise ValueError("Mã địa điểm chưa hợp lệ.")
    return os.path.join(AUDIO_DIR, f"{poi_id}_{lang}.mp3")


def valid_audio(path):
    try:
        with open(path, "rb") as stream:
            header = stream.read(3)
        return os.path.getsize(path) > 128 and (header == b"ID3" or len(header) >= 2 and header[0] == 255 and header[1] & 224 == 224)
    except OSError:
        return False


def _metadata_path(path):
    return Path(path).with_suffix(".json")


def write_metadata(path, metadata):
    target = _metadata_path(path)
    fd, temporary = tempfile.mkstemp(dir=target.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(metadata, stream, ensure_ascii=False, indent=2)
        os.replace(temporary, target)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _read_metadata(path):
    try:
        data = json.loads(_metadata_path(path).read_text(encoding="utf-8"))
        if not isinstance(data, dict) or not valid_audio(path):
            return None
        if data.get("audio_sha256") != hashlib.sha256(Path(path).read_bytes()).hexdigest():
            return None
        if data.get("text_sha256") != text_hash(data.get("text", "")):
            return None
        return data
    except (OSError, ValueError, TypeError, AttributeError):
        return None


async def _edge_save(text, lang, path):
    import edge_tts
    await asyncio.wait_for(edge_tts.Communicate(text, VOICES[lang], connect_timeout=5, receive_timeout=10).save(path), timeout=20)


def _run_edge(text, lang, path):
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(_edge_save(text, lang, path))
    # Sync tool may also be used from a notebook/async caller; never nest asyncio.run.
    with ThreadPoolExecutor(max_workers=1) as executor:
        return executor.submit(lambda: asyncio.run(_edge_save(text, lang, path))).result(timeout=25)


def _gtts_save(text, lang, path):
    from gtts import gTTS
    gTTS(text, lang=GTTS_LANG[lang], timeout=(5, 12)).save(path)


def synthesize_result(text: str, lang: str, out_path: str) -> dict:
    validate_language(lang)
    if not isinstance(text, str) or not text.strip() or len(text) > 6000:
        raise ValueError("Nội dung thuyết minh phải có từ 1 đến 6000 ký tự.")
    target = Path(out_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    for provider, save in (("edge-tts", _run_edge), ("gtts", _gtts_save)):
        fd, temporary = tempfile.mkstemp(dir=target.parent, suffix=".mp3")
        os.close(fd)
        try:
            save(text, lang, temporary)
            if not valid_audio(temporary):
                raise ValueError("Empty or invalid MP3")
            os.replace(temporary, target)
            return {"audio_path": str(target), "tts_status": "ready", "tts_provider": provider}
        except Exception as error:
            logger.warning("TTS provider %s failed (%s)", provider, type(error).__name__)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
    return {"audio_path": None, "tts_status": "unavailable", "tts_provider": None,
            "warning": "Chưa tạo được audio từ cả hai dịch vụ. Bạn vẫn có thể đọc nội dung thuyết minh."}


def synthesize(text: str, lang: str, out_path: str) -> str | None:
    return synthesize_result(text, lang, out_path)["audio_path"]


def get_audio_result(poi_id: str, lang: str, text: str) -> dict:
    path = audio_path(poi_id, lang)
    if not isinstance(text, str) or not text.strip() or len(text) > 6000:
        raise ValueError("Nội dung thuyết minh phải có từ 1 đến 6000 ký tự.")
    digest = text_hash(text)
    with _guard:
        lock = _locks.setdefault(path, threading.Lock())
    with lock:
        metadata = _read_metadata(path)
        if metadata and metadata.get("text_sha256") == digest and metadata.get("lang") == lang:
            return {"audio_path": path, "tts_status": "cached", "tts_provider": metadata.get("provider"), "audio_version": digest[:16]}
        result = synthesize_result(text, lang, path)
        if result["audio_path"]:
            write_metadata(path, {"text": text, "text_sha256": digest, "lang": lang,
                                  "audio_sha256": hashlib.sha256(Path(path).read_bytes()).hexdigest(),
                                  "provider": result["tts_provider"], "created_at": dt.datetime.now(dt.timezone.utc).isoformat()})
            result["audio_version"] = digest[:16]
        return result


def get_or_create_audio(poi_id: str, lang: str, text: str) -> str | None:
    return get_audio_result(poi_id, lang, text)["audio_path"]


def load_prepared_audio(poi_id, lang, context=None):
    path = audio_path(poi_id, lang)
    metadata = _read_metadata(path)
    if not metadata or metadata.get("lang") != lang or metadata.get("approved") is not True or not metadata.get("prepared"):
        return None
    if context is not None and metadata.get("context_sha256") != text_hash(context):
        return None
    return {"text": metadata["text"], "audio_path": path, "audio_version": metadata["text_sha256"][:16],
            "tts_status": "cached", "tts_provider": metadata.get("provider"), "source": "prepared", "mock": False}
