"""Huy — đăng ký tool cho LLM + chuyển lời gọi tool sang các module.

TOOL_SCHEMAS: định dạng tool của OpenAI Chat Completions (Gemini OpenAI-compatible dùng chung được).
dispatch(): chạy tool theo tên, lưu kết quả quan trọng vào state (vd lịch trình hiện tại).
"""
import json

from config import DEFAULT_END_TIME, DEFAULT_START, DEFAULT_START_TIME, USE_MOCK
from rag.search import get_poi_context, search_pois
from routing.optimizer import plan_route
from services.tts import audio_path, get_or_create_audio
from services.weather import get_weather

GROUP_TYPES = ["family", "elderly", "couple", "friends", "solo"]

TOOL_SCHEMAS = [
    {"type": "function", "function": {
        "name": "search_pois",
        "description": "Tìm điểm tham quan ở Hà Nội đã lọc theo giá vé/người, nhóm khách, trong nhà, ngày đóng cửa.",
        "parameters": {"type": "object", "properties": {
            "interests": {"type": "array", "items": {"type": "string"},
                          "description": "vd history, food, museum, cafe, nature, shopping, night, art"},
            "group_type": {"type": "string", "enum": GROUP_TYPES},
            "max_price": {"type": "integer", "description": "giá vé tối đa mỗi người, VND"},
            "indoor_only": {"type": "boolean"},
            "top_k": {"type": "integer"},
            "date": {"type": "string", "description": "YYYY-MM-DD"},
        }, "required": ["interests", "group_type", "max_price"]}}},
    {"type": "function", "function": {
        "name": "plan_route",
        "description": "Xếp lịch trình: thứ tự, giờ đến/đi, chi phí, điểm bị bỏ. Mọi số liệu lấy từ đây, không tự tính.",
        "parameters": {"type": "object", "properties": {
            "poi_ids": {"type": "array", "items": {"type": "string"}},
            "start_lat": {"type": "number"}, "start_lng": {"type": "number"},
            "start_time": {"type": "string", "description": "HH:MM"},
            "end_time": {"type": "string", "description": "HH:MM"},
            "budget_vnd": {"type": "integer"},
            "n_people": {"type": "integer"},
            "vehicle": {"type": "string", "enum": ["car", "motorbike", "walk"]},
            "date": {"type": "string", "description": "YYYY-MM-DD"},
        }, "required": ["poi_ids", "budget_vnd", "n_people"]}}},
    {"type": "function", "function": {
        "name": "get_weather",
        "description": "Dự báo mưa theo giờ ở Hà Nội. is_rainy=true thì ưu tiên điểm trong nhà.",
        "parameters": {"type": "object", "properties": {
            "date": {"type": "string", "description": "YYYY-MM-DD"},
        }, "required": ["date"]}}},
    {"type": "function", "function": {
        "name": "narrate",
        "description": "Tạo lời thuyết minh + audio cho một điểm, bằng ngôn ngữ lang (vi/en/ko/ja/zh).",
        "parameters": {"type": "object", "properties": {
            "poi_id": {"type": "string"}, "lang": {"type": "string"},
        }, "required": ["poi_id", "lang"]}}},
]

NARRATE_SYSTEM = ("Bạn là hướng dẫn viên. Viết lời thuyết minh 60–90 giây bằng ngôn ngữ mã '%s'. "
                  "CHỈ dùng nội dung được cung cấp, không bịa năm, số liệu hay giai thoại.")


def narrate(poi_id: str, lang: str) -> dict:
    from agent.llm import call_llm  # import trễ để tránh vòng import
    ctx = get_poi_context(poi_id, lang)
    if not ctx:
        return {"text": "", "audio_path": None}
    text = call_llm(NARRATE_SYSTEM % lang, ctx, mock_reply="[MOCK thuyết minh] " + ctx)
    if USE_MOCK:  # không gọi TTS khi mock, chỉ dùng file đã pre-generate nếu có
        import os
        path = audio_path(poi_id, lang)
        return {"text": text, "audio_path": path if os.path.exists(path) else None}
    return {"text": text, "audio_path": get_or_create_audio(poi_id, lang, text)}


def _slim_poi(p: dict) -> dict:
    keys = ["id", "name", "category", "tags", "indoor", "price_vnd", "open", "close",
            "closed_days", "visit_minutes", "notes_vi", "notes_en"]
    return {k: p[k] for k in keys if k in p}


def dispatch(name: str, args: dict, state: dict):
    """Chạy tool, cập nhật state, trả kết quả gọn để đưa lại cho LLM."""
    date = args.get("date") or state.get("date")
    if name == "search_pois":
        res = search_pois(args.get("interests", []), args.get("group_type", "friends"),
                          int(args.get("max_price", 10**9)), bool(args.get("indoor_only", False)),
                          int(args.get("top_k", 15)), date)
        return [_slim_poi(p) for p in res]
    if name == "plan_route":
        start = (args.get("start_lat", DEFAULT_START[0]), args.get("start_lng", DEFAULT_START[1]))
        plan = plan_route(args["poi_ids"], start, args.get("start_time", DEFAULT_START_TIME),
                          args.get("end_time", DEFAULT_END_TIME), int(args["budget_vnd"]),
                          int(args["n_people"]), args.get("vehicle", "car"), date)
        state["plan"] = plan
        return {k: v for k, v in plan.items() if k != "polyline"}  # polyline dài, LLM không cần
    if name == "get_weather":
        w = get_weather(date or args["date"], *DEFAULT_START)
        state["weather"] = w
        return w
    if name == "narrate":
        return narrate(args["poi_id"], args.get("lang", "vi"))
    return {"error": "tool không tồn tại: %s" % name}


def dumps(obj) -> str:
    return json.dumps(obj, ensure_ascii=False)
