"""Open-Meteo forecast; explicit mock only, never fabricate a fallback forecast."""
import copy
import datetime as dt
import json
import math
import os
import threading
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen

import config  # loads .env; weather is independent of the LLM mock flag

RAIN_THRESHOLD = 60
TIMEZONE = dt.timezone(dt.timedelta(hours=7))
API_URL = "https://api.open-meteo.com/v1/forecast"
CACHE_SECONDS = 300
_cache = {}
_cache_lock = threading.Lock()


def _unavailable(date, message, code):
    return {"date": date, "rain_prob_by_hour": {}, "is_rainy": None, "temp_max": None,
            "mock": False, "status": "unavailable", "source": "open-meteo", "error": message,
            "error_code": code, "timezone": "Asia/Bangkok"}


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def get_weather(date: str, lat: float, lng: float) -> dict:
    """Return forecast + provenance. Unknown rain is None, never a false 'no rain'."""
    try:
        day = dt.date.fromisoformat(date)
        if day.isoformat() != date or not _number(lat) or not _number(lng) or not -90 <= lat <= 90 or not -180 <= lng <= 180:
            raise ValueError
    except (TypeError, ValueError):
        return _unavailable(date, "Ngày hoặc tọa độ chưa hợp lệ.", "invalid_input")
    mode = os.environ.get("WEATHER_MODE", "real").strip().lower() or "real"
    if mode == "mock":
        rain = {f"{hour:02d}:00": 70 if 13 <= hour <= 17 else 10 for hour in range(24)}
        return {"date": date, "rain_prob_by_hour": rain, "is_rainy": True, "temp_max": 27.0,
                "mock": True, "status": "mock", "source": "mock", "timezone": "Asia/Bangkok"}
    if mode != "real":
        return _unavailable(date, "WEATHER_MODE phải là real hoặc mock.", "invalid_config")
    today = dt.datetime.now(TIMEZONE).date()
    if not today <= day <= today + dt.timedelta(days=15):
        return _unavailable(date, "Ngày đi nằm ngoài phạm vi dự báo 16 ngày. Hãy chọn ngày gần hơn.", "out_of_range")
    key = (date, lat, lng)
    with _cache_lock:
        cached = _cache.get(key)
        if cached and time.monotonic() - cached[0] < CACHE_SECONDS:
            return {**copy.deepcopy(cached[1]), "cached": True}
    query = urlencode({"latitude": lat, "longitude": lng, "hourly": "precipitation_probability,temperature_2m",
                       "timezone": "Asia/Bangkok", "start_date": date, "end_date": date})
    try:
        with urlopen(f"{API_URL}?{query}", timeout=8) as response:
            payload = json.load(response)
        hourly = payload["hourly"]
        timestamps, probabilities, temperatures = (hourly[k] for k in ("time", "precipitation_probability", "temperature_2m"))
        if not timestamps or len(timestamps) != len(probabilities) or len(timestamps) != len(temperatures):
            raise ValueError("Incomplete hourly arrays")
        rain, temps = {}, []
        for timestamp, probability, temperature in zip(timestamps, probabilities, temperatures):
            parsed = dt.datetime.fromisoformat(timestamp)
            if parsed.date() != day:
                continue
            if _number(probability) and 0 <= probability <= 100:
                rain[parsed.strftime("%H:%M")] = probability
            if _number(temperature):
                temps.append(temperature)
        if not rain and not temps:
            raise ValueError("No forecast values")
        complete = len(rain) == 24 and len(temps) == 24
        is_rainy = True if any(value >= RAIN_THRESHOLD for value in rain.values()) else False if len(rain) == 24 else None
        result = {"date": date, "rain_prob_by_hour": rain, "is_rainy": is_rainy,
                  "temp_max": max(temps) if temps else None, "mock": False,
                  "status": "ok" if complete else "partial", "source": "open-meteo", "cached": False,
                  "timezone": "Asia/Bangkok", "fetched_at": dt.datetime.now(TIMEZONE).isoformat(),
                  "warning": None if complete else "Dữ liệu theo giờ chưa đầy đủ; các trường chưa rõ được để trống."}
        with _cache_lock:
            _cache[key] = (time.monotonic(), copy.deepcopy(result))
            for old_key, (created, _) in list(_cache.items()):
                if time.monotonic() - created >= CACHE_SECONDS:
                    _cache.pop(old_key, None)
        return result
    except (HTTPError, URLError, TimeoutError, OSError):
        return _unavailable(date, "Chưa kết nối được Open-Meteo. Vui lòng thử lại sau.", "network_error")
    except (ValueError, TypeError, KeyError):
        return _unavailable(date, "Open-Meteo chưa có dữ liệu hợp lệ cho ngày này.", "invalid_response")
