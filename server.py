"""API cho frontend React (Cường). Chạy: python -m uvicorn server:app --reload --port 8000

Chưa có LLM_API_KEY trong .env → chạy MOCK (agent luật đơn giản, dữ liệu giả).
Session (lịch sử chat + lịch trình hiện tại) giữ trong RAM theo session_id do frontend sinh.
"""
import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from agent.llm import chat, new_state
from agent.tools import narrate
from config import AUDIO_DIR, DEFAULT_END_TIME, DEFAULT_START, DEFAULT_START_TIME, SUPPORTED_LANGS, USE_MOCK, USE_TOMTOM
from rag.search import get_poi, load_pois, search_pois
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
        stops.append({**s, "name": p.get("name"), "lat": p.get("lat"), "lng": p.get("lng")})
    reasons = plan.get("dropped_reasons", {})
    dropped = [{"poi_id": i, "name": (get_poi(i) or {}).get("name"), "reason": reasons.get(i)} for i in plan["dropped"]]
    return {**plan, "stops": stops, "dropped": dropped}


class ChatIn(BaseModel):
    session_id: str
    message: str
    date: str | None = None


class NarrateIn(BaseModel):
    poi_id: str
    lang: str = "vi"


class SummaryIn(BaseModel):
    session_id: str
    lang: str = "vi"


@app.get("/api/config")
def get_config():
    return {"mock": USE_MOCK, "langs": SUPPORTED_LANGS, "center": DEFAULT_START}


@app.post("/api/chat")
def post_chat(body: ChatIn):
    state = _session(body.session_id, body.date)
    reply, state = chat(body.message, state)
    return {"reply": reply, "plan": _enrich(state.get("plan")), "weather": state.get("weather")}


@app.post("/api/reset")
def post_reset(body: SummaryIn):
    SESSIONS.pop(body.session_id, None)
    return {"ok": True}


@app.get("/api/pois")
def list_pois():
    return load_pois()


@app.get("/api/pois/{poi_id}")
def one_poi(poi_id: str):
    p = get_poi(poi_id)
    if not p:
        raise HTTPException(404, "Không có POI %s" % poi_id)
    return p


@app.get("/api/weather")
def weather(date: str):
    return get_weather(date, *DEFAULT_START)


@app.post("/api/narrate")
def post_narrate(body: NarrateIn):
    n = narrate(body.poi_id, body.lang)
    url = "/audio/" + os.path.basename(n["audio_path"]) if n.get("audio_path") else None
    return {"text": n["text"], "audio_url": url}


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
