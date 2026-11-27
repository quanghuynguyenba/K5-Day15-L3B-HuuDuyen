"""Huy — client LLM, prompt, vòng lặp tool calling.

Hai hàm cho cả nhóm dùng:
    call_llm(system, user, mock_reply) -> str          gọi LLM một lần (thuyết minh, tóm tắt…)
    chat(user_text, state) -> (reply: str, state)      một lượt chat của khách; state giữ ràng buộc + lịch trình

USE_MOCK (chưa có LLM_API_KEY): chat() chạy luật đơn giản thay LLM để UI và tool test được end-to-end.
Thật: SDK `openai` (OpenAI, hoặc Gemini qua LLM_BASE_URL OpenAI-compatible). Không dùng LangChain.
"""
import json
import re

from config import (DEFAULT_END_TIME, DEFAULT_START, DEFAULT_START_TIME, LLM_API_KEY, LLM_BASE_URL,
                    LLM_MODEL, USE_MOCK)

MAX_STEPS = 6  # số vòng tool calling tối đa mỗi lượt chat

SYSTEM = """Bạn là trợ lý du lịch Hà Nội.
- Trả lời đúng ngôn ngữ khách đang dùng. Tên điểm luôn kèm tên tiếng Việt trong ngoặc.
- Tách ràng buộc: ngân sách (VND), giờ bắt đầu/kết thúc, nhóm khách (family/elderly/couple/friends/solo),
  số người, sở thích. Thiếu thì hỏi lại TỐI ĐA 1 câu; còn lại dùng mặc định: 2 người, %s–%s, friends.
- Lập lịch: gọi search_pois rồi plan_route. KHÔNG tự tính khoảng cách, giờ, tiền — chỉ dùng số plan_route trả về.
  Điểm trong "dropped" thì giải thích ngắn vì sao bỏ (hết giờ, vượt ngân sách, đóng cửa).
- Khách sửa lịch ("bỏ bảo tàng", "bớt 200k"): gọi lại tool với ràng buộc mới, dựa trên lịch hiện tại.
- Hỏi về mưa: gọi get_weather; is_rainy thì tìm lại với indoor_only=true cho khung giờ mưa.
- Khách báo đang ở đâu / bị trễ giữa chuyến: gọi plan_route cho phần còn lại của ngày với start_lat/start_lng
  = vị trí hiện tại, start_time = giờ hiện tại, bỏ các điểm đã đi.
- Hỏi về một điểm (giờ mở, giá, lưu ý): chỉ trả lời theo dữ liệu tool; không có thì nói không có.
""" % (DEFAULT_START_TIME, DEFAULT_END_TIME)

_client = None


def _get_client():
    global _client
    if _client is None:
        from openai import OpenAI
        _client = OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)
    return _client


def call_llm(system: str, user: str, mock_reply: str = "[MOCK]") -> str:
    if USE_MOCK:
        return mock_reply
    r = _get_client().chat.completions.create(
        model=LLM_MODEL, messages=[{"role": "system", "content": system}, {"role": "user", "content": user}])
    return r.choices[0].message.content or ""


def new_state(date: str | None = None) -> dict:
    return {"history": [], "constraints": {}, "plan": None, "weather": None, "date": date}


def chat(user_text: str, state: dict) -> tuple[str, dict]:
    reply = _chat_mock(user_text, state) if USE_MOCK else _chat_llm(user_text, state)
    state["history"] += [{"role": "user", "content": user_text}, {"role": "assistant", "content": reply}]
    return reply, state


# ---------------------------------------------------------------- LLM thật
def _chat_llm(user_text: str, state: dict) -> str:
    from agent.tools import TOOL_SCHEMAS, dispatch, dumps
    ctx = {"date": state.get("date"), "current_plan": state.get("plan") and
           {k: v for k, v in state["plan"].items() if k != "polyline"}}
    msgs = [{"role": "system", "content": SYSTEM + "\nTrạng thái hiện tại: " + dumps(ctx)}]
    msgs += state["history"][-10:]
    msgs.append({"role": "user", "content": user_text})
    client = _get_client()
    for _ in range(MAX_STEPS):
        r = client.chat.completions.create(model=LLM_MODEL, messages=msgs, tools=TOOL_SCHEMAS)
        m = r.choices[0].message
        if not m.tool_calls:
            return m.content or ""
        msgs.append(m.model_dump(exclude_none=True))
        for tc in m.tool_calls:
            try:
                result = dispatch(tc.function.name, json.loads(tc.function.arguments or "{}"), state)
            except Exception as e:  # trả lỗi cho LLM thay vì làm sập app
                result = {"error": str(e)}
            msgs.append({"role": "tool", "tool_call_id": tc.id, "content": dumps(result)})
    return "Xin lỗi, tôi chưa xếp xong lịch trình. Bạn thử nói lại ngắn hơn nhé."


# ---------------------------------------------------------------- MOCK (luật đơn giản, chỉ để test luồng)
INTEREST_WORDS = {
    "history": ["lịch sử", "history", "역사", "歴史", "历史"],
    "food": ["ẩm thực", "ăn", "food", "음식", "料理", "美食"],
    "museum": ["bảo tàng", "museum", "박물관", "博物館", "博物馆"],
    "nature": ["thiên nhiên", "hồ", "nature", "lake"],
}


def detect_lang(text: str) -> str:
    if re.search(r"[가-힯]", text):
        return "ko"
    if re.search(r"[぀-ヿ]", text):
        return "ja"
    if re.search(r"[一-鿿]", text):
        return "zh"
    if re.search(r"[ăâđêôơưạảấầẩẫậắằẳẵặẹẻẽếềểễệỉịọỏốồổỗộớờởỡợụủứừửữựỳỵỷỹ]", text.lower()):
        return "vi"
    return "en"


def _money(num: str, unit: str) -> int:
    n = float(num.replace(",", "."))
    return int(n * (1_000_000 if unit in ("triệu", "tr", "m") else 1_000 if unit in ("k", "nghìn") else 1))


def _chat_mock(text: str, state: dict) -> str:
    from agent.tools import dispatch
    from rag.search import get_poi
    t = text.lower()
    c = state["constraints"]
    c.setdefault("budget_vnd", 1_000_000)
    c.setdefault("n_people", 2)
    c.setdefault("interests", ["history"])
    c.setdefault("start_time", DEFAULT_START_TIME)
    c.setdefault("start", DEFAULT_START)
    c["lang"] = detect_lang(text)

    m = re.search(r"bớt\s*(\d+[.,]?\d*)\s*(k|nghìn|triệu|tr)", t)
    if m:
        c["budget_vnd"] = max(0, c["budget_vnd"] - _money(m.group(1), m.group(2)))
    else:
        m = re.search(r"(\d+[.,]?\d*)\s*(triệu|tr|k|nghìn)", t)
        if m:
            c["budget_vnd"] = _money(m.group(1), m.group(2))
        else:
            m = re.search(r"\b(\d{1,3}(?:[.,]\d{3})+|\d+)\s*(?:đ|vnd)\b", t)
            if m:
                c["budget_vnd"] = int(re.sub(r"[.,]", "", m.group(1)))
    m = re.search(r"(\d+)\s*(người|people|명|人)", t)
    if m:
        c["n_people"] = int(m.group(1))
    found = [k for k, words in INTEREST_WORDS.items() if any(w in t for w in words)]
    if found and not re.search(r"bớt|trễ|mưa", t):
        c["interests"] = found
    indoor = "trong nhà" in t or "indoor" in t
    if re.search(r"mưa|rain|비|雨", t):
        indoor = indoor or dispatch("get_weather", {"date": state.get("date") or "2026-11-28"}, state)["is_rainy"]
    m = re.search(r"trễ\s*(\d+)\s*(tiếng|giờ|h)", t)
    if m:
        h, mi = map(int, c["start_time"].split(":"))
        c["start_time"] = "%02d:%02d" % (h + int(m.group(1)), mi)
    if "hồ gươm" in t or "hoàn kiếm" in t:
        c["start"] = DEFAULT_START

    pois = dispatch("search_pois", {"interests": c["interests"] + ["food"], "group_type": "friends",
                                    "max_price": c["budget_vnd"], "indoor_only": indoor}, state)
    plan = dispatch("plan_route", {"poi_ids": [p["id"] for p in pois], "start_lat": c["start"][0],
                                   "start_lng": c["start"][1], "start_time": c["start_time"],
                                   "budget_vnd": c["budget_vnd"], "n_people": c["n_people"]}, state)
    lines = ["[MOCK — chưa nối LLM] lang=%s · %d người · ngân sách %s VND%s" % (
        c["lang"], c["n_people"], f"{c['budget_vnd']:,}", " · chỉ điểm trong nhà" if indoor else "")]
    for i, s in enumerate(plan["stops"], 1):
        lines.append("%d. %s–%s %s (%s VND)" % (i, s["arrive"], s["depart"],
                                                 get_poi(s["poi_id"])["name"]["vi"], f"{s['cost']:,}"))
    lines.append("Tổng: %s VND · %d phút" % (f"{plan['total_cost']:,}", plan["total_minutes"]))
    if plan["dropped"]:
        lines.append("Bỏ: " + ", ".join(plan["dropped"]))
    return "\n".join(lines)
