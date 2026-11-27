"""Hiếu — tìm POI + lấy nội dung cho thuyết minh.

Bản hiện tại là MOCK: đọc thẳng data/pois.json, xếp hạng bằng số tag trùng với interests.
TODO (Hiếu): đọc SQLite (data/pois.db) + xếp hạng bằng vector similarity (data/cache/poi_vectors.npy).
"""
import datetime as dt
import json
import os
from functools import lru_cache

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

WEEKDAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


@lru_cache(maxsize=1)
def load_pois() -> list:
    with open(os.path.join(DATA_DIR, "pois.json"), encoding="utf-8") as f:
        return json.load(f)


def get_poi(poi_id: str) -> dict | None:
    return next((p for p in load_pois() if p["id"] == poi_id), None)


def weekday_of(date: str | None) -> str | None:
    """'2026-11-28' → 'sat'. None → None."""
    if not date:
        return None
    return WEEKDAYS[dt.date.fromisoformat(date).weekday()]


def is_open_on(poi: dict, date: str | None) -> bool:
    wd = weekday_of(date)
    return wd is None or wd not in poi.get("closed_days", [])


def is_schedulable(poi: dict) -> bool:
    """Chỉ lập lịch khi biết giá và khoảng giờ; không đoán dữ liệu còn thiếu."""
    return (isinstance(poi.get("price_vnd"), int) and poi["price_vnd"] >= 0
            and isinstance(poi.get("open"), str) and isinstance(poi.get("close"), str)
            and poi["open"] < poi["close"])


def search_pois(interests: list[str], group_type: str, max_price: int,
                indoor_only: bool = False, top_k: int = 15, date: str | None = None) -> list[dict]:
    """Lọc cứng (giá / người, nhóm khách, indoor, ngày đóng cửa) rồi xếp hạng theo interests."""
    interests = [i.lower() for i in interests or []]
    out = []
    for p in load_pois():
        if not is_schedulable(p):
            continue
        if p["price_vnd"] > max_price:
            continue
        if group_type and group_type not in p["suitable_for"]:
            continue
        if indoor_only and not p["indoor"]:
            continue
        if not is_open_on(p, date):
            continue
        # MOCK ranking — thay bằng cosine similarity
        score = sum(1 for t in p["tags"] + [p["category"]] if t in interests)
        if interests and score == 0:
            continue
        out.append((score, p))
    out.sort(key=lambda x: -x[0])
    return [p for _, p in out[:top_k]]


def get_poi_context(poi_id: str, lang: str) -> str:
    """Đoạn nội dung làm căn cứ cho thuyết minh. Chưa có bản ngôn ngữ đó thì dùng en → vi."""
    p = get_poi(poi_id)
    if not p:
        return ""
    for l in (lang, "en", "vi"):
        desc = p.get("description_%s" % l)
        if desc:
            notes = p.get("notes_%s" % l, "")
            price = f"{p['price_vnd']} VND" if p.get("price_vnd") is not None else "chưa có dữ liệu"
            hours = f"{p['open']}–{p['close']}" if p.get("open") and p.get("close") else "chưa có dữ liệu"
            return f"{desc}\n{notes}\nGiá vé: {price} · Giờ mở: {hours}"
    return ""
