"""Tùng — Goong Distance Matrix / Directions + cache.

Bản hiện tại là MOCK: Haversine × 1.4 / tốc độ nội thành, polyline là đường thẳng.
TODO (Tùng):
  - distance_matrix gọi Goong /DistanceMatrix, cache ra data/cache/matrix.json
  - directions gọi Goong /Direction, decode bằng thư viện `polyline`
  - fallback: OSRM → Haversine (giữ hàm _haversine_km dưới đây)
"""
import math

from config import GOONG_API_KEY, USE_MOCK  # noqa: F401

SPEED_KMH = {"car": 20, "motorbike": 25, "walk": 4.5}
DETOUR = 1.4


def _haversine_km(a: tuple, b: tuple) -> float:
    lat1, lng1, lat2, lng2 = map(math.radians, (*a, *b))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lng2 - lng1) / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(h))


def travel_minutes(a: tuple, b: tuple, vehicle: str = "car") -> int:
    km = _haversine_km(a, b) * DETOUR
    return max(1, round(km / SPEED_KMH.get(vehicle, 20) * 60))


def distance_matrix(points: list[tuple], vehicle: str = "car") -> list[list[int]]:
    """Ma trận phút di chuyển giữa các điểm (lat, lng)."""
    return [[0 if i == j else travel_minutes(a, b, vehicle) for j, b in enumerate(points)]
            for i, a in enumerate(points)]


def directions(points: list[tuple], vehicle: str = "car") -> list[list[float]]:
    """Polyline [[lat, lng], …] đi qua các điểm theo thứ tự. MOCK: nối thẳng."""
    return [[lat, lng] for lat, lng in points]
