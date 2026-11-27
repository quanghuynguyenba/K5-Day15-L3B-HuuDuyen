"""API cho frontend React (Cường). Chạy: python -m uvicorn server:app --reload --port 8000

Chưa có LLM_API_KEY trong .env → chạy MOCK (agent luật đơn giản, dữ liệu giả).
Session (lịch sử chat + lịch trình hiện tại) giữ trong RAM theo session_id do frontend sinh.
"""
import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Literal

from agent.llm import chat, new_state
from agent.tools import narrate
from config import AUDIO_DIR, DEFAULT_START, SUPPORTED_LANGS, USE_MOCK
from rag.search import get_poi, load_pois
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
    dropped = [{"poi_id": i, "name": (get_poi(i) or {}).get("name")} for i in plan["dropped"]]
    return {**plan, "stops": stops, "dropped": dropped}


class ChatIn(BaseModel):
    session_id: str
    message: str
    date: str | None = None


class NarrateIn(BaseModel):
    poi_id: str
    lang: Literal["vi", "en", "ko", "ja", "zh"] = "vi"


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
    if not get_poi(body.poi_id):
        raise HTTPException(404, "Không tìm thấy địa điểm để thuyết minh.")
    try:
        n = narrate(body.poi_id, body.lang)
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
