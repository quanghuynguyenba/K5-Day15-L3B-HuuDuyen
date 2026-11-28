"""Cấu hình chung (cả nhóm). Đọc .env, không cần python-dotenv.

USE_MOCK = True → agent dùng dữ liệu giả khi chưa có LLM_API_KEY.
Thời tiết dùng WEATHER_MODE=real|mock riêng, mặc định real.
"""
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(ROOT, "data")
CACHE_DIR = os.path.join(DATA_DIR, "cache")
AUDIO_DIR = os.path.join(ROOT, "audio")


def _load_env(path=os.path.join(ROOT, ".env")):
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k, v = k.strip(), v.strip().strip('"').strip("'")
            # Dòng trống không được che dòng có giá trị phía sau (.env chép từ bản có khối trùng tên).
            # Biến môi trường đặt sẵn ngoài .env vẫn được ưu tiên.
            if v and (k not in os.environ or k in _from_file):
                os.environ[k] = v
                _from_file.add(k)
            elif k not in os.environ:
                os.environ[k] = v
                _from_file.add(k)


_from_file = set()


_load_env()

LLM_API_KEY = os.environ.get("LLM_API_KEY", "").strip()
LLM_MODEL = os.environ.get("LLM_MODEL", "").strip()
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "").strip() or None
TOMTOM_API_KEY = os.environ.get("TOMTOM_API_KEY", "").strip()
EMBED_API_KEY = os.environ.get("EMBED_API_KEY", "").strip()

USE_MOCK = os.environ.get("USE_MOCK", "").strip().lower() in ("1", "true", "yes") or not LLM_API_KEY
# TomTom độc lập với LLM: có key là dùng đường thật, không thì Haversine. Tắt hẳn: USE_TOMTOM=0
USE_TOMTOM = bool(TOMTOM_API_KEY) and os.environ.get("USE_TOMTOM", "1").strip().lower() not in ("0", "false", "no")

# Điểm xuất phát mặc định: Hồ Hoàn Kiếm
DEFAULT_START = (21.0285, 105.8542)
DEFAULT_START_TIME = "08:00"
DEFAULT_END_TIME = "18:00"
SUPPORTED_LANGS = ["vi", "en", "ko", "ja", "zh"]
