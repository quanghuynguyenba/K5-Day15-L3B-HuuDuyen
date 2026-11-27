"""Công cụ của lát cắt lịch một ngày ở Hà Nội: weather, POIs, RAG, Goong route, budget, itinerary."""
import datetime as dt
import json
import math
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

import knowledge
from tracing import tool

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POI_PATH = os.path.join(ROOT, "data", "pois.json")
WEATHER_PATH = os.path.join(ROOT, "data", "weather.json")
TRANSFER_MINUTES = 15
HANOI_CENTER = (21.0285, 105.8542)
SPEED_KMH = {"car": 20.0, "motorbike": 25.0, "walk": 4.5}
DETOUR = 1.4


def _load(path: str):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _minutes(hhmm: str) -> int:
    hour, minute = hhmm.split(":")
    return int(hour) * 60 + int(minute)


def _clock(minutes: int) -> str:
    return "%02d:%02d" % (minutes // 60, minutes % 60)


def _price(poi: dict):
    raw = poi.get("price_vnd")
    if raw is None:
        return None
    return int(raw)


def _label(poi: dict) -> str:
    name = poi.get("name")
    if isinstance(name, dict):
        return name.get("vi") or name.get("en") or poi.get("id")
    return name or poi.get("id")


def _haversine_km(a: tuple[float, float], b: tuple[float, float]) -> float:
    lat1, lng1, lat2, lng2 = map(math.radians, (*a, *b))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lng2 - lng1) / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(h))


@tool
def get_weather(date: str, user_says_rain: bool = False) -> dict:
    """Đọc thời tiết ngày đi (Open-Meteo khi WEATHER_MODE=real, fallback synthetic).
    Input: date (str), user_says_rain (bool). Output: is_rainy, temp_max, source.
    Không tác động ra ngoài."""
    row = _load(WEATHER_PATH)
    target_date = date or row.get("date") or "2026-11-28"
    if user_says_rain:
        return {
            "date": target_date,
            "is_rainy": True,
            "temp_max": row.get("temp_max"),
            "source": "user",
        }

    weather_mode = (os.environ.get("WEATHER_MODE") or "synthetic").strip().lower()
    if weather_mode == "real":
        try:
            day = dt.date.fromisoformat(target_date)
            today = dt.date.today()
            if today <= day <= today + dt.timedelta(days=15):
                q = urllib.parse.urlencode({
                    "latitude": HANOI_CENTER[0],
                    "longitude": HANOI_CENTER[1],
                    "hourly": "precipitation_probability,temperature_2m",
                    "timezone": "Asia/Bangkok",
                    "start_date": target_date,
                    "end_date": target_date,
                })
                with urllib.request.urlopen(f"https://api.open-meteo.com/v1/forecast?{q}", timeout=4) as resp:
                    payload = json.loads(resp.read().decode("utf-8"))
                probs = payload.get("hourly", {}).get("precipitation_probability") or []
                temps = payload.get("hourly", {}).get("temperature_2m") or []
                if probs:
                    return {
                        "date": target_date,
                        "is_rainy": any(p >= 60 for p in probs if p is not None),
                        "temp_max": max(t for t in temps if t is not None) if temps else row.get("temp_max"),
                        "source": "open-meteo",
                    }
        except Exception:
            pass

    return {
        "date": target_date,
        "is_rainy": bool(row.get("is_rainy")),
        "temp_max": row.get("temp_max"),
        "source": row.get("source"),
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
        price = _price(poi)
        if price is None or not poi.get("open") or not poi.get("close"):
            continue
        cost = price * int(n_people)
        if cost > int(budget_vnd):
            continue
        found.append(dict(poi))
    found.sort(key=lambda p: (_price(p), int(p["visit_minutes"]), p["id"]))
    return found


@tool
def plan_route(poi_ids: list, start_time: str, end_time: str,
               budget_vnd: int, n_people: int) -> dict:
    """Xếp thứ tự, giờ đến và tiền bằng code.
    Input: poi_ids, start_time, end_time, budget_vnd, n_people.
    Output: stops, total_cost, total_minutes, dropped, transfer_minutes, feasible.
    Không đặt vé, không trừ tiền."""
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
        price = _price(poi)
        if price is None or not poi.get("open") or not poi.get("close"):
            dropped.append({"poi_id": poi_id, "name": _label(poi), "reason": "không có giờ hoặc giá"})
            continue
        open_at = _minutes(poi["open"])
        close_at = _minutes(poi["close"])
        if arrive < open_at:
            arrive = open_at
        depart = arrive + int(poi["visit_minutes"])
        cost = price * int(n_people)
        if arrive > end or depart > end or depart > close_at:
            dropped.append({"poi_id": poi_id, "name": _label(poi), "reason": "hết giờ"})
            continue
        if spent + cost > int(budget_vnd):
            dropped.append({"poi_id": poi_id, "name": _label(poi), "reason": "vượt ngân sách"})
            continue
        stops.append({
            "poi_id": poi_id,
            "name": _label(poi),
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


@tool
def retrieve_knowledge(query: str, top_k: int = 5, lang: str = "vi",
                       indoor_only: bool = False, category: str = "") -> list:
    """Truy xuất thông tin điểm tham quan Hà Nội từ PostgreSQL + pgvector (hoặc JSON fallback).
    Input: query (str), top_k (int), lang (str), indoor_only (bool), category (str).
    Output: danh sách chunk gồm poi_id, name, content, source, score.
    Không tác động ra ngoài."""
    filters: dict[str, Any] = {"lang": lang}
    if indoor_only:
        filters["indoor_only"] = True
    if category:
        filters["category"] = category
    return knowledge.retrieve(query, top_k=top_k, filters=filters)


@tool
def get_place_details(poi_id: str, lang: str = "vi") -> dict:
    """Đọc chi tiết một điểm từ PostgreSQL hoặc data/pois.json.
    Input: poi_id (str), lang (str). Output: thông tin có nguồn hoặc lỗi không có trong dữ liệu.
    Không tác động ra ngoài."""
    poi = knowledge.get_poi_by_id(poi_id)
    if not poi:
        return {"found": False, "poi_id": poi_id, "message": knowledge.EMPTY_MSG}
    ctx = knowledge.get_poi_context(poi_id, lang=lang)
    return {
        "found": True,
        "poi_id": poi["id"],
        "name": _label(poi),
        "price_vnd": poi.get("price_vnd"),
        "open": poi.get("open"),
        "close": poi.get("close"),
        "indoor": bool(poi.get("indoor")),
        "source": poi.get("source") or "data/pois.json",
        "context": ctx,
    }


@tool
def get_route(poi_ids: list, vehicle: str = "car") -> dict:
    """Tính thời gian di chuyển giữa các điểm qua Goong DistanceMatrix (nếu có GOONG_API_KEY) hoặc Haversine.
    Input: poi_ids (list[str]), vehicle ('car'|'motorbike'|'walk').
    Output: segments, total_transfer_minutes, source. Không tác động ra ngoài."""
    catalog = {p["id"]: p for p in _load(POI_PATH)}
    coords = []
    for pid in poi_ids or []:
        poi = catalog.get(pid)
        if poi and poi.get("lat") is not None and poi.get("lng") is not None:
            coords.append((pid, float(poi["lat"]), float(poi["lng"])))
    if len(coords) < 2:
        return {"segments": [], "total_transfer_minutes": 0, "source": "synthetic"}

    goong_key = (os.environ.get("GOONG_API_KEY") or "").strip()
    goong_vehicle = {"car": "car", "motorbike": "bike", "walk": "foot"}.get(vehicle, "car")
    if goong_key:
        try:
            origins = "|".join(f"{lat},{lng}" for _, lat, lng in coords[:-1])
            destinations = "|".join(f"{lat},{lng}" for _, lat, lng in coords[1:])
            q = urllib.parse.urlencode({
                "origins": origins,
                "destinations": destinations,
                "vehicle": goong_vehicle,
                "api_key": goong_key,
            })
            with urllib.request.urlopen(f"https://rsapi.goong.io/DistanceMatrix?{q}", timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            rows = data.get("rows") or []
            segments = []
            for idx in range(len(coords) - 1):
                elem = rows[idx]["elements"][idx]
                mins = max(1, round(elem["duration"]["value"] / 60))
                segments.append({"from": coords[idx][0], "to": coords[idx + 1][0], "minutes": mins})
            return {
                "segments": segments,
                "total_transfer_minutes": sum(s["minutes"] for s in segments),
                "source": "goong",
            }
        except Exception:
            pass

    speed = SPEED_KMH.get(vehicle, 20.0)
    segments = []
    for idx in range(len(coords) - 1):
        a = (coords[idx][1], coords[idx][2])
        b = (coords[idx + 1][1], coords[idx + 1][2])
        mins = max(1, round(_haversine_km(a, b) * DETOUR / speed * 60))
        segments.append({"from": coords[idx][0], "to": coords[idx + 1][0], "minutes": mins})
    return {
        "segments": segments,
        "total_transfer_minutes": sum(s["minutes"] for s in segments),
        "source": "haversine_fallback",
    }


@tool
def estimate_budget(poi_ids: list, n_people: int = 2) -> dict:
    """Tính tổng chi phí vé dự kiến từ dữ liệu POI.
    Input: poi_ids (list[str]), n_people (int). Output: items, total_cost, unknown_price_pois.
    Không tác động ra ngoài."""
    catalog = {p["id"]: p for p in _load(POI_PATH)}
    items = []
    unknown = []
    total = 0
    people = max(1, int(n_people))
    for pid in poi_ids or []:
        poi = catalog.get(pid)
        if not poi:
            unknown.append(pid)
            continue
        price = _price(poi)
        if price is None:
            unknown.append(_label(poi))
            continue
        cost = price * people
        total += cost
        items.append({"poi_id": pid, "name": _label(poi), "unit_price": price, "cost": cost})
    return {
        "n_people": people,
        "items": items,
        "total_cost": total,
        "unknown_price_pois": unknown,
        "note": "Chỉ tính giá vé/suất có trong dữ liệu; không tự bịa chi phí phát sinh.",
    }


@tool
def create_itinerary(poi_ids: list, start_time: str, end_time: str,
                     budget_vnd: int, n_people: int) -> dict:
    """Tạo lịch nháp 1 ngày ở Hà Nội (bọc plan_route, không đặt vé).
    Input: poi_ids, start_time, end_time, budget_vnd, n_people. Output: kết quả plan_route.
    Không tác động ra ngoài."""
    return plan_route(poi_ids, start_time, end_time, budget_vnd, n_people)


@tool
def update_itinerary(poi_ids: list, start_time: str, end_time: str,
                     budget_vnd: int, n_people: int) -> dict:
    """Cập nhật lịch nháp 1 ngày ở Hà Nội theo ràng buộc mới (bọc plan_route, không đặt vé).
    Input: poi_ids, start_time, end_time, budget_vnd, n_people. Output: kết quả plan_route.
    Không tác động ra ngoài."""
    return plan_route(poi_ids, start_time, end_time, budget_vnd, n_people)


TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Kiểm tra thời tiết ngày đi ở Hà Nội. is_rainy=true thì chỉ xếp điểm trong nhà.",
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {"type": "string", "description": "YYYY-MM-DD"},
                    "user_says_rain": {"type": "boolean"},
                },
                "required": ["date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_pois",
            "description": "Tìm và lọc danh sách điểm tham quan Hà Nội theo sở thích, ngân sách, trong nhà, ngày đóng cửa.",
            "parameters": {
                "type": "object",
                "properties": {
                    "interests": {"type": "array", "items": {"type": "string"}},
                    "indoor_only": {"type": "boolean"},
                    "exclude_categories": {"type": "array", "items": {"type": "string"}},
                    "closed_day": {"type": "string"},
                    "budget_vnd": {"type": "integer"},
                    "n_people": {"type": "integer"},
                },
                "required": ["interests", "indoor_only", "exclude_categories", "closed_day", "budget_vnd", "n_people"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "plan_route",
            "description": "Xếp lịch nháp theo giờ mở cửa và ngân sách. Mọi số liệu giờ/tiền lấy từ đây.",
            "parameters": {
                "type": "object",
                "properties": {
                    "poi_ids": {"type": "array", "items": {"type": "string"}},
                    "start_time": {"type": "string", "description": "HH:MM"},
                    "end_time": {"type": "string", "description": "HH:MM"},
                    "budget_vnd": {"type": "integer"},
                    "n_people": {"type": "integer"},
                },
                "required": ["poi_ids", "start_time", "end_time", "budget_vnd", "n_people"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "retrieve_knowledge",
            "description": "Truy xuất RAG từ PostgreSQL + pgvector cho câu hỏi tìm điểm, gợi ý, giờ mở cửa, giá vé.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "top_k": {"type": "integer"},
                    "lang": {"type": "string"},
                    "indoor_only": {"type": "boolean"},
                    "category": {"type": "string"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_place_details",
            "description": "Lấy thông tin chi tiết một điểm theo poi_id.",
            "parameters": {
                "type": "object",
                "properties": {
                    "poi_id": {"type": "string"},
                    "lang": {"type": "string"},
                },
                "required": ["poi_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_route",
            "description": "Ước tính thời gian di chuyển giữa các điểm (Goong hoặc Haversine).",
            "parameters": {
                "type": "object",
                "properties": {
                    "poi_ids": {"type": "array", "items": {"type": "string"}},
                    "vehicle": {"type": "string", "enum": ["car", "motorbike", "walk"]},
                },
                "required": ["poi_ids"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "estimate_budget",
            "description": "Tính tổng tiền vé dự kiến cho danh sách poi_ids và số người.",
            "parameters": {
                "type": "object",
                "properties": {
                    "poi_ids": {"type": "array", "items": {"type": "string"}},
                    "n_people": {"type": "integer"},
                },
                "required": ["poi_ids", "n_people"],
            },
        },
    },
]

TOOL_ALLOWLIST = {
    "get_weather",
    "search_pois",
    "plan_route",
    "retrieve_knowledge",
    "get_place_details",
    "get_route",
    "estimate_budget",
    "create_itinerary",
    "update_itinerary",
}


def dispatch(name: str, args: dict, state: dict) -> Any:
    """Validate tool name and arguments against allowlist, execute, and update state."""
    if name not in TOOL_ALLOWLIST:
        return {"error": f"Tool '{name}' is not allowed."}
    if not isinstance(args, dict):
        return {"error": "Tool arguments must be a JSON object."}
    try:
        if name == "get_weather":
            res = get_weather(str(args.get("date") or "2026-11-28"), bool(args.get("user_says_rain", False)))
            state["weather"] = res
            return res
        if name == "search_pois":
            res = search_pois(
                list(args.get("interests") or []),
                bool(args.get("indoor_only", False)),
                list(args.get("exclude_categories") or []),
                str(args.get("closed_day") or ""),
                int(args["budget_vnd"]),
                int(args["n_people"]),
            )
            return [{"id": p["id"], "name": _label(p), "price_vnd": p.get("price_vnd"),
                     "open": p.get("open"), "close": p.get("close"), "indoor": p.get("indoor")} for p in res]
        if name in ("plan_route", "create_itinerary", "update_itinerary"):
            res = plan_route(
                list(args["poi_ids"]),
                str(args["start_time"]),
                str(args["end_time"]),
                int(args["budget_vnd"]),
                int(args["n_people"]),
            )
            state["plan"] = res
            return res
        if name == "retrieve_knowledge":
            return retrieve_knowledge(
                str(args["query"]),
                top_k=min(int(args.get("top_k", 5)), 10),
                lang=str(args.get("lang", "vi")),
                indoor_only=bool(args.get("indoor_only", False)),
                category=str(args.get("category") or ""),
            )
        if name == "get_place_details":
            return get_place_details(str(args["poi_id"]), lang=str(args.get("lang", "vi")))
        if name == "get_route":
            return get_route(list(args["poi_ids"]), vehicle=str(args.get("vehicle", "car")))
        if name == "estimate_budget":
            return estimate_budget(list(args["poi_ids"]), n_people=int(args.get("n_people", 2)))
    except (KeyError, TypeError, ValueError) as e:
        return {"error": f"Invalid arguments for {name}: {e}"}
    except Exception as e:
        return {"error": f"Tool execution error in {name}: {e}"}
