"""Cường — thời tiết từ Open-Meteo (miễn phí, không cần key).

Bản hiện tại là MOCK: trả "chiều mưa" cố định để demo bước "trời mưa thì sao".
TODO (Cường): gọi https://api.open-meteo.com/v1/forecast
    ?latitude=..&longitude=..&hourly=precipitation_probability,temperature_2m
    &timezone=Asia/Bangkok&start_date=<date>&end_date=<date>
  rồi tính rain_prob_by_hour / is_rainy / temp_max; lỗi mạng thì trả MOCK.
"""
from config import USE_MOCK  # noqa: F401

RAIN_THRESHOLD = 60  # % — từ ngưỡng này coi là mưa


def get_weather(date: str, lat: float, lng: float) -> dict:
    rain = {"%02d:00" % h: (70 if 13 <= h <= 17 else 10) for h in range(6, 22)}
    return {
        "rain_prob_by_hour": rain,
        "is_rainy": any(v >= RAIN_THRESHOLD for v in rain.values()),
        "temp_max": 27.0,
        "mock": True,
    }
