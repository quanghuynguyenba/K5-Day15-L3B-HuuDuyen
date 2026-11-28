"""API cho frontend React (Cường). Chạy: python -m uvicorn server:app --reload --port 8000

Chưa có LLM_API_KEY trong .env → chạy MOCK (agent luật đơn giản, dữ liệu giả).
Session (lịch sử chat + lịch trình hiện tại) giữ trong RAM theo session_id do frontend sinh.
"""
import asyncio
import logging
import os
import threading

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Literal

from agent.llm import chat, new_state
from agent.tools import NarrationCancelled, narrate
from config import AUDIO_DIR, DEFAULT_END_TIME, DEFAULT_START, DEFAULT_START_TIME, SUPPORTED_LANGS, USE_MOCK, USE_TOMTOM
from rag.search import get_poi, load_pois, is_schedulable, search_pois
from routing import maps
from routing.optimizer import plan_route
from routing.validate import validate_plan
from routing.summary import summarize_trip, trip_facts
from services.weather import get_weather

app = FastAPI(title="Hanoi Trip API")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"], allow_methods=["*"],
                   allow_headers=["*"])
os.makedirs(AUDIO_DIR, exist_ok=True)
app.mount("/audio", StaticFiles(directory=AUDIO_DIR), name="audio")

SESSIONS: dict[str, dict] = {}


def _session(sid: str, date: str | None = None) -> dict:
    s = SESSIONS.setdefault(sid, new_state(date))
    if date:
        s["date"] = date
    return s


def _enrich(plan: dict | None) -> dict | None:
    """Thêm tên + toạ độ vào từng stop để frontend vẽ map, không phải gọi thêm API."""
    if not plan:
        return None
    stops = []
    for s in plan["stops"]:
        p = get_poi(s["poi_id"]) or {}
        stops.append({
            **s,
            "name": p.get("name"), "lat": p.get("lat"), "lng": p.get("lng"),
            "description_vi": p.get("description_vi"),
            "description_en": p.get("description_en"),
        })
    reasons = plan.get("dropped_reasons", {})
    dropped = [{"poi_id": i, "name": (get_poi(i) or {}).get("name"), "reason": reasons.get(i)} for i in plan["dropped"]]
    return {**plan, "stops": stops, "dropped": dropped}


class Location(BaseModel):
    lat: float
    lng: float
    accuracy: float | None = None


class ChatIn(BaseModel):
    session_id: str
    message: str
    date: str | None = None
    location: Location | None = None  # GPS trình duyệt; None = chưa có / bị từ chối


# Chỉ dùng GPS làm điểm xuất phát khi khách đang ở quanh Hà Nội (dữ liệu POI chỉ có Hà Nội)
MAX_START_KM = 40


def _accept_location(loc: "Location | None"):
    """→ (location dict hoặc None, ghi chú). Ngoài vùng Hà Nội thì bỏ qua, xuất phát từ Hồ Gươm."""
    if loc is None:
        return None, "Chưa có vị trí — xuất phát từ Hồ Gươm."
    if not (-90 <= loc.lat <= 90 and -180 <= loc.lng <= 180):
        return None, "Toạ độ không hợp lệ — xuất phát từ Hồ Gươm."
    km = maps._haversine_km((loc.lat, loc.lng), DEFAULT_START)
    if km > MAX_START_KM:
        return None, "Bạn đang cách Hà Nội ~%d km — lịch trình xuất phát từ Hồ Gươm." % km
    return {"lat": loc.lat, "lng": loc.lng, "accuracy": loc.accuracy}, "Xuất phát từ vị trí hiện tại của bạn."


class NarrateIn(BaseModel):
    poi_id: str
    lang: Literal["vi", "en", "ko", "ja", "zh"] = "vi"


class SummaryIn(BaseModel):
    session_id: str
    lang: str = "vi"


@app.get("/api/config")
def get_config():
    pois = load_pois()
    return {"mock": USE_MOCK, "langs": SUPPORTED_LANGS, "center": DEFAULT_START,
            "poi_count": len(pois), "schedulable_poi_count": sum(is_schedulable(poi) for poi in pois),
            "data_source": "repo-pois"}


@app.post("/api/chat")
def post_chat(body: ChatIn):
    state = _session(body.session_id, body.date)
    state["location"], location_note = _accept_location(body.location)
    reply, state = chat(body.message, state)
    plan = _enrich(state.get("plan"))
    if plan is not None:
        plan["n_people"] = state.get("constraints", {}).get("n_people")
        start = state.get("plan_start") or DEFAULT_START
        plan["start"] = {"lat": start[0], "lng": start[1],
                         "source": "gps" if state["location"] and tuple(start) == (state["location"]["lat"], state["location"]["lng"])
                         else "default" if tuple(start) == tuple(DEFAULT_START) else "chat"}
    return {"reply": reply, "plan": plan, "weather": state.get("weather"),
            "location": {"used": state["location"] is not None, "note": location_note}}


@app.post("/api/reset")
def post_reset(body: SummaryIn):
    SESSIONS.pop(body.session_id, None)
    return {"ok": True}


@app.get("/api/pois")
def list_pois():
    return [_poi_view(poi) for poi in load_pois()]


def _poi_view(poi):
    """Expose data completeness; a URL is not a claim of independent verification."""
    missing = []
    if poi.get("price_vnd") is None:
        missing.append("price")
    if not poi.get("open") or not poi.get("close"):
        missing.append("opening_hours")
    return {**poi, "data_source": "repo-pois", "schedulable": is_schedulable(poi), "missing_fields": missing}


@app.get("/api/pois/{poi_id}")
def one_poi(poi_id: str):
    p = get_poi(poi_id)
    if not p:
        raise HTTPException(404, "Không có POI %s" % poi_id)
    return _poi_view(p)


@app.get("/api/weather")
def weather(date: str):
    return get_weather(date, *DEFAULT_START)


@app.post("/api/narrate")
async def post_narrate(body: NarrateIn, request: Request):
    """Chạy narrate trong thread; cứ ~0,3 giây kiểm client còn kết nối không. Người dùng đóng popup
    (frontend abort fetch) → báo narrate dừng trước bước LLM / TTS và trả 499, không tạo file audio."""
    if not get_poi(body.poi_id):
        raise HTTPException(404, "Không tìm thấy địa điểm để thuyết minh.")
    cancel = threading.Event()
    job = asyncio.get_running_loop().run_in_executor(None, narrate, body.poi_id, body.lang, cancel)
    while not job.done():
        if await request.is_disconnected():
            cancel.set()
            logging.getLogger("uvicorn.error").info("Client huỷ thuyết minh %s/%s — dừng", body.poi_id, body.lang)
            job.add_done_callback(lambda f: f.exception())  # nuốt lỗi của job đã bị huỷ
            return Response(status_code=499)
        await asyncio.wait({job}, timeout=0.3)
    try:
        n = job.result()
    except NarrationCancelled:
        return Response(status_code=499)
    except ValueError as error:
        raise HTTPException(400, str(error)) from error
    except Exception as error:
        raise HTTPException(503, "Chưa tạo được thuyết minh. Vui lòng thử lại sau.") from error
    url = "/audio/" + os.path.basename(n["audio_path"]) if n.get("audio_path") else None
    if url and n.get("audio_version"):
        url += "?v=" + n["audio_version"]
    return {**{key: value for key, value in n.items() if key != "audio_path"}, "audio_url": url}


@app.post("/api/summary")
def post_summary(body: SummaryIn):
    state = SESSIONS.get(body.session_id)
    if not state or not state.get("plan") or not state["plan"]["stops"]:
        raise HTTPException(400, "Chưa có lịch trình")
    return {"facts": trip_facts(state["plan"]), "summary": summarize_trip(state["plan"], body.lang)}


# ---------------------------------------------------------------- trang xem bản đồ (frontend/maps.html) — gọi thẳng plan_route, không qua LLM
class RouteIn(BaseModel):
    poi_ids: list[str] = []
    # poi_ids rỗng → tự tìm ứng viên bằng search_pois (giống agent): interests, group_type, indoor_only
    interests: list[str] = []
    group_type: str = "friends"
    indoor_only: bool = False
    start: tuple[float, float] = DEFAULT_START
    start_time: str = DEFAULT_START_TIME
    end_time: str = DEFAULT_END_TIME
    budget_vnd: int = 10_000_000
    n_people: int = 1
    vehicle: str = "car"
    date: str | None = None
    solver: str = "auto"  # auto | greedy


@app.post("/api/route")
def post_route(body: RouteIn):
    import time as _t
    before = dict(maps.stats)
    ids = body.poi_ids or [p["id"] for p in search_pois(body.interests, body.group_type, 10**9,
                                                         body.indoor_only, 15, body.date)]
    t0 = _t.perf_counter()
    plan = plan_route(ids, body.start, body.start_time, body.end_time,
                      body.budget_vnd, body.n_people, body.vehicle, body.date, body.solver)
    elapsed = round(_t.perf_counter() - t0, 2)
    violations = validate_plan(plan, body.start_time, body.end_time, body.budget_vnd, body.n_people, body.date)
    return {
        "plan": _enrich(plan),
        "candidates": len(ids),
        "violations": violations,
        "seconds": elapsed,
        "routing": {
            "provider": "tomtom" if USE_TOMTOM else "haversine",
            "api_calls": maps.stats["api_calls"] - before["api_calls"],
            "fallback_pairs": maps.stats["fallback_pairs"] - before["fallback_pairs"],
        },
    }


class DirectionsIn(BaseModel):
    points: list[tuple[float, float]]
    vehicle: str = "car"


@app.post("/api/directions")
def post_directions(body: DirectionsIn):
    """Tuyến cố định qua các điểm theo thứ tự (dùng cho tuyến mẫu trên maps.html)."""
    if len(body.points) < 2:
        raise HTTPException(400, "Cần ít nhất 2 điểm")
    before = dict(maps.stats)
    m = maps.distance_matrix(body.points, body.vehicle)
    legs = [m[i][i + 1] for i in range(len(body.points) - 1)]
    poly = maps.directions(body.points, body.vehicle)
    km = sum(maps._haversine_km(a, b) for a, b in zip(poly, poly[1:]))
    return {
        "polyline": poly,
        "leg_minutes": legs,
        "total_minutes": sum(legs),
        "km": round(km, 1),
        "routing": {
            "provider": "tomtom" if USE_TOMTOM else "haversine",
            "api_calls": maps.stats["api_calls"] - before["api_calls"],
            "fallback_pairs": maps.stats["fallback_pairs"] - before["fallback_pairs"],
        },
    }
