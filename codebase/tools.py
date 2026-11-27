"""Công cụ của lát cắt lịch một ngày ở Hà Nội. CP2: dữ liệu synthetic, chưa gọi API ngoài.

Mỗi hàm: tên · input · output · có tác động ra ngoài không.
"""
import json
import os

from tracing import tool

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POI_PATH = os.path.join(ROOT, "data", "pois.json")
WEATHER_PATH = os.path.join(ROOT, "data", "weather.json")
TRANSFER_MINUTES = 15


def _load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _minutes(hhmm):
    hour, minute = hhmm.split(":")
    return int(hour) * 60 + int(minute)


def _clock(minutes):
    return "%02d:%02d" % (minutes // 60, minutes % 60)


@tool
def get_weather(date: str, user_says_rain: bool = False) -> dict:
    """Đọc thời tiết ngày đi.
    Input: date (str), user_says_rain (bool). Output: is_rainy, temp_max, source.
    Không tác động ra ngoài. CP2 đọc file synthetic; câu nói có mưa thì coi là trời mưa."""
    row = _load(WEATHER_PATH)
    rainy = bool(user_says_rain) or bool(row.get("is_rainy"))
    return {
        "date": date or row.get("date"),
        "is_rainy": rainy,
        "temp_max": row.get("temp_max"),
        "source": "user" if user_says_rain else row.get("source"),
    }


@tool
def search_pois(interests: list, indoor_only: bool, exclude_categories: list,
                closed_day: str, budget_vnd: int, n_people: int) -> list:
    """Lọc điểm trong data/pois.json.
    Input: interests, indoor_only, exclude_categories, closed_day, budget_vnd, n_people.
    Output: danh sách điểm còn đủ rẻ cho một lượt (giá × số người ≤ ngân sách).
    Không tác động ra ngoài."""
    want = set(interests or [])
    skip = set(exclude_categories or [])
    found = []
    for poi in _load(POI_PATH):
        if closed_day and closed_day in poi.get("closed_days", []):
            continue
        if poi.get("category") in skip:
            continue
        if indoor_only and not poi.get("indoor"):
            continue
        tags = set(poi.get("tags") or [])
        if want and not (tags & want):
            continue
        cost = int(poi["price_vnd"]) * int(n_people)
        if cost > int(budget_vnd):
            continue
        found.append(dict(poi))
    found.sort(key=lambda p: (int(p["price_vnd"]), int(p["visit_minutes"]), p["id"]))
    return found


@tool
def plan_route(poi_ids: list, start_time: str, end_time: str,
               budget_vnd: int, n_people: int) -> dict:
    """Xếp thứ tự, giờ đến và tiền bằng code.
    Input: poi_ids, start_time, end_time, budget_vnd, n_people.
    Output: stops, total_cost, total_minutes, dropped, transfer_minutes.
    Không đặt vé, không trừ tiền. Thời gian di chuyển CP2 là 15 phút cố định, chưa gọi Goong."""
    catalog = {p["id"]: p for p in _load(POI_PATH)}
    start = _minutes(start_time)
    end = _minutes(end_time)
    cursor = start
    spent = 0
    stops = []
    dropped = []
    first = True
    for poi_id in poi_ids:
        poi = catalog.get(poi_id)
        if not poi:
            dropped.append({"poi_id": poi_id, "reason": "không có trong dữ liệu"})
            continue
        travel = 0 if first else TRANSFER_MINUTES
        arrive = cursor + travel
        open_at = _minutes(poi["open"])
        close_at = _minutes(poi["close"])
        if arrive < open_at:
            arrive = open_at
        depart = arrive + int(poi["visit_minutes"])
        cost = int(poi["price_vnd"]) * int(n_people)
        if arrive > end or depart > end or depart > close_at:
            dropped.append({"poi_id": poi_id, "name": poi["name"], "reason": "hết giờ"})
            continue
        if spent + cost > int(budget_vnd):
            dropped.append({"poi_id": poi_id, "name": poi["name"], "reason": "vượt ngân sách"})
            continue
        stops.append({
            "poi_id": poi_id,
            "name": poi["name"],
            "arrive": _clock(arrive),
            "depart": _clock(depart),
            "cost": cost,
            "indoor": bool(poi.get("indoor")),
        })
        spent += cost
        cursor = depart
        first = False
    return {
        "stops": stops,
        "total_cost": spent,
        "total_minutes": cursor - start,
        "dropped": dropped,
        "transfer_minutes": TRANSFER_MINUTES,
        "feasible": bool(stops),
    }
