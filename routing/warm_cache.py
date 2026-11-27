"""Tùng — tính sẵn ma trận thời gian (TomTom) cho toàn bộ POI trước demo.

Chạy:  python -m routing.warm_cache            (car)
       python -m routing.warm_cache walk
Kết quả ghi vào data/cache/maps_cache.json → commit file này để máy demo không cần mạng.
"""
import sys

from config import DEFAULT_START, USE_TOMTOM
from rag.search import load_pois
from routing import maps


def main(vehicle: str = "car"):
    if not USE_TOMTOM:
        sys.exit("Chưa có TOMTOM_API_KEY trong .env (hoặc USE_TOMTOM=0) — không có gì để tính sẵn.")
    points = [DEFAULT_START] + [(p["lat"], p["lng"]) for p in load_pois()]
    maps.distance_matrix(points, vehicle)
    n = len(points)
    print("%d điểm · %d cặp · %d lần gọi TomTom · %d cặp vẫn phải dùng Haversine" % (
        n, n * (n - 1), maps.stats["api_calls"], maps.stats["fallback_pairs"]))
    print("Cache:", maps.CACHE_PATH)


if __name__ == "__main__":
    main(*(sys.argv[1:2]))
