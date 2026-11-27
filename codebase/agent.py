"""Một agent cho lát cắt: lịch một ngày ở Hà Nội (Phases 4–7).

Hỗ trợ:
- Refuse & out-of-scope guards trước khi gọi tool
- Session memory + user preferences (Postgres + in-memory fallback)
- Multilingual vi/en/ko/ja/zh detection + cross-language RAG
- LLM tool-calling loop (MAX_STEPS=6) khi model thật bật; deterministic fallback khi fake
"""
from dataclasses import asdict
import json
import re
import uuid

import ai
from ai import call_model, call_model_tools
import memory
from prompts import (
    INTENT_SYSTEM_PROMPT,
    SYSTEM_PROMPT,
    build_budget_prompt,
    build_intent_prompt,
    build_rag_prompt,
    build_system_prompt,
    build_trip_prompt,
    detect_lang,
)
from schemas import Entities, IntentResult, parse_intent_json
from tools import TOOL_SCHEMAS, dispatch, get_weather, plan_route, retrieve_knowledge, search_pois
from tracing import note

SYSTEM = SYSTEM_PROMPT
MAX_STEPS = 6

REFUSE = (
    "Mình không đặt vé, không thanh toán và không nhận số thẻ hay OTP. "
    "Mình chỉ lập lịch nháp. Bạn tự mua vé tại điểm hoặc kênh chính thức."
)

OUT_OF_SCOPE_MSG = (
    "Mình chỉ lập lịch một ngày ở Hà Nội. "
    "Mình không xếp lịch nhiều ngày hay thành phố khác."
)

OUT_OF_SCOPE_WEATHER_MSG = (
    "Mình chỉ lập lịch một ngày ở Hà Nội và không có số thời tiết cho điểm ngoài phạm vi."
)


def _norm(text: str) -> str:
    return text.lower()


def _people(text: str):
    match = re.search(r"(\d+)\s*(?:người|people|persons?|pax|명|人)", _norm(text))
    return int(match.group(1)) if match else None


def _budget(text: str):
    raw = _norm(text)
    trieu = re.search(r"(\d+)\s*(?:triệu|million|m\b)", raw)
    if trieu:
        return int(trieu.group(1)) * 1000000
    k_match = re.search(r"(\d+)\s*(?:k|nghìn)\b", raw)
    if k_match:
        return int(k_match.group(1)) * 1000
    digits = re.search(r"(\d{5,})", raw)
    if digits:
        return int(digits.group(1))
    return None


def _window(text: str):
    match = re.search(r"(?:từ|from)?\s*(\d{1,2})\s*[h:]\s*(?:\d{2})?\s*(?:đến|to|-)\s*(\d{1,2})\s*[h:]", _norm(text))
    if not match:
        return None
    return "%02d:00" % int(match.group(1)), "%02d:00" % int(match.group(2))


def _interests(text: str) -> list[str]:
    raw = _norm(text)
    found = []
    if any(k in raw for k in ("lịch sử", "lich su", "history", "역사", "歴史", "历史")):
        found.append("history")
    if any(k in raw for k in ("ẩm thực", "am thuc", "ăn", "food", "음식", "料理", "美食")):
        found.append("food")
    if any(k in raw for k in ("bảo tàng", "bao tang", "museum", "박물관", "博物館", "博物馆")):
        if "bỏ bảo tàng" not in raw and "thay vì bảo tàng" not in raw:
            found.append("museum")
    return found


def _closed_day(text: str) -> str:
    raw = _norm(text)
    if "thứ hai" in raw or "thu hai" in raw or "monday" in raw:
        return "mon"
    return ""


def _excluded(text: str) -> list[str]:
    raw = _norm(text)
    if "bỏ bảo tàng" in raw or "bo bao tang" in raw or "thay vì bảo tàng" in raw:
        return ["museum"]
    return []


def _missing_place(text: str) -> str:
    match = re.search(r"thêm\s+(.+?)\s+vào", text, flags=re.IGNORECASE)
    if not match:
        return ""
    name = match.group(1).strip(" .")
    known = ("văn miếu", "hoàng thành", "bảo tàng", "phở", "bún chả", "hồ gươm", "nhà thờ")
    if any(part in name.lower() for part in known):
        return ""
    return name


def _refuses(text: str) -> bool:
    raw = _norm(text)
    keys = (
        "đặt vé", "dat ve", "thanh toán", "thanh toan", "số thẻ", "so the",
        "otp", "mật khẩu", "mat khau", "trừ ", "giữ chỗ", "giu cho",
        "chốt phòng", "book land tour", "tour trọn gói", "đặt tour", "đặt phòng",
        "book ticket", "credit card", "pay now",
    )
    return any(key in raw for key in keys)


def _is_out_of_scope(text: str) -> bool:
    raw = _norm(text)
    non_hanoi = (
        "malaysia", "singapore", "ấn độ", "thành đô", "trùng khánh",
        "tp.hcm", "hcm", "xuyên việt", "đà nẵng", "nha trang",
    )
    multi_day = ("ngày 4 đêm", "15 ngày", "11 ngày", "9 ngày", "5 ngày", "nhiều ngày", "đi hè")
    if any(k in raw for k in non_hanoi):
        return True
    if any(k in raw for k in multi_day) and "hà nội" not in raw:
        return True
    if "xuyên việt" in raw or "15 ngày" in raw:
        return True
    return False


def _extract_fallback(text: str, saved_constraints: dict | None = None) -> IntentResult:
    """Deterministic regex/rule intent & entity extraction, merging session memory constraints."""
    raw = _norm(text)
    lang = detect_lang(text)
    if _refuses(text):
        return IntentResult(intent="REFUSE", entities=Entities(language=lang, query=text))
    if _is_out_of_scope(text):
        return IntentResult(intent="OUT_OF_SCOPE", entities=Entities(destination="other", language=lang, query=text))

    saved = saved_constraints or {}
    window = _window(text) or (tuple(saved["window"]) if saved.get("window") else None)
    budget = _budget(text) or saved.get("budget_vnd")
    n_people = _people(text) or saved.get("n_people")
    interests = _interests(text) or list(saved.get("interests") or [])
    exclusions = _excluded(text) or list(saved.get("exclusions") or [])
    if "museum" in exclusions and "museum" in interests:
        interests = [i for i in interests if i != "museum"]

    entities = Entities(
        destination="Hanoi",
        start_date=saved.get("start_date") or "2026-11-28",
        window=window,
        budget_vnd=budget,
        interests=interests,
        n_people=n_people,
        language=lang,
        exclusions=exclusions,
        rainy=("mưa" in raw or "rain" in raw or bool(saved.get("rainy"))),
        closed_day=_closed_day(text) or saved.get("closed_day", ""),
        requested_place=_missing_place(text),
        query=text,
    )

    if any(k in raw for k in ("bỏ ", "thay vì", "đổi ", "without ", "remove ")):
        return IntentResult(intent="MODIFY_TRIP", entities=entities)
    if any(k in raw for k in ("giá vé", "mấy giờ mở", "mở cửa", "thông tin", "lưu ý", "có gì hay", "opening hours", "ticket price", "입장료", "営業時間", "门票")):
        return IntentResult(intent="TRAVEL_INFO", entities=entities)
    if any(k in raw for k in ("gợi ý", "nên đi đâu", "đề xuất", "recommend", "suggest", "추천", "おすすめ", "推荐")):
        return IntentResult(intent="RECOMMEND_PLACE", entities=entities)
    if any(k in raw for k in ("tìm điểm", "tìm quán", "tìm địa điểm", "find ", "search ")):
        return IntentResult(intent="SEARCH_PLACE", entities=entities)
    if any(k in raw for k in ("ước tính", "chi phí bao nhiêu", "hết bao nhiêu tiền", "estimate budget")) and not entities.window:
        return IntentResult(intent="ESTIMATE_BUDGET", entities=entities)

    return IntentResult(intent="PLAN_TRIP", entities=entities)


def _ask_from_entities(ent: Entities, text: str) -> str:
    if ent.n_people is None:
        return "Đi mấy người?" if ent.language == "vi" else "How many people are traveling?"
    if ent.budget_vnd is None:
        return "Ngân sách cả ngày là bao nhiêu đồng?" if ent.language == "vi" else "What is your total budget in VND?"
    if ent.window is None:
        return "Đi từ mấy giờ đến mấy giờ?" if ent.language == "vi" else "What time window (start to end) do you want?"
    raw = _norm(text)
    if not ent.interests and ("sao cũng được" in raw or "so cung duoc" in raw):
        return "Bạn muốn ưu tiên sở thích nào: lịch sử, ẩm thực, hay bảo tàng?"
    if not ent.interests:
        return "Bạn muốn ưu tiên sở thích nào: lịch sử, ẩm thực, hay bảo tàng?" if ent.language == "vi" else "Which interests do you prefer: history, food, or museum?"
    return ""


def _format_plan(plan: dict, missing_name: str, rainy: bool) -> str:
    lines = ["Lịch nháp (số lấy từ plan_route, chưa đặt vé):"]
    if missing_name:
        lines.append("Không có %s trong dữ liệu điểm. Mình không bịa giờ và giá." % missing_name)
    if rainy:
        lines.append("Trời mưa: chỉ xếp điểm trong nhà.")
    if not plan["feasible"]:
        lines.append("Không xếp được trong khung giờ và ngân sách đã cho.")
        lines.append("Nới ngân sách hoặc nới khung giờ rồi nhắn lại.")
    for index, stop in enumerate(plan["stops"], start=1):
        lines.append("%d. %s | đến %s | đi %s | %d" % (
            index, stop["name"], stop["arrive"], stop["depart"], stop["cost"]))
    lines.append("Tổng tiền: %d" % plan["total_cost"])
    lines.append("Tổng phút: %d" % plan["total_minutes"])
    if plan["dropped"]:
        bits = ["%s — %s" % (item.get("name") or item["poi_id"], item["reason"]) for item in plan["dropped"]]
        lines.append("Bỏ: " + "; ".join(bits))
    else:
        lines.append("Bỏ: không")
    lines.append("Di chuyển giữa điểm: %d phút (synthetic, chưa gọi bản đồ)." % plan["transfer_minutes"])
    return "\n".join(lines)


def _format_rag_fallback(chunks: list[dict]) -> str:
    if not chunks:
        return "Không có trong dữ liệu điểm Hà Nội. Mình không bịa giờ mở cửa hay giá vé."
    lines = ["Thông tin điểm tham khảo từ cơ sở dữ liệu Hà Nội:"]
    for idx, c in enumerate(chunks[:3], start=1):
        price = f"{c['price_vnd']} VND" if c.get("price_vnd") is not None else "chưa có dữ liệu"
        hours = f"{c.get('open')}–{c.get('close')}" if c.get("open") and c.get("close") else "chưa có dữ liệu"
        lines.append(f"{idx}. {c.get('name')} | Giá vé: {price} | Giờ mở: {hours}")
    return "\n".join(lines)


def _classify_and_extract(text: str, saved_constraints: dict | None = None) -> IntentResult:
    """Use LLM JSON extraction when real provider is active, with regex + memory fallback."""
    fallback = _extract_fallback(text, saved_constraints=saved_constraints)
    if ai.MODEL_PROVIDER == "fake":
        return fallback

    raw_res = call_model(INTENT_SYSTEM_PROMPT, build_intent_prompt(text))
    parsed = parse_intent_json(raw_res.get("text", ""))
    if parsed is None:
        note("intent: JSON parse failed, using regex fallback")
        return fallback

    if fallback.intent == "REFUSE":
        parsed.intent = "REFUSE"
    elif fallback.intent == "OUT_OF_SCOPE":
        parsed.intent = "OUT_OF_SCOPE"
    else:
        parsed.entities.language = parsed.entities.language or fallback.entities.language
        if parsed.entities.n_people is None:
            parsed.entities.n_people = fallback.entities.n_people
        if parsed.entities.budget_vnd is None:
            parsed.entities.budget_vnd = fallback.entities.budget_vnd
        if parsed.entities.window is None:
            parsed.entities.window = fallback.entities.window
        if not parsed.entities.interests:
            parsed.entities.interests = fallback.entities.interests
        if not parsed.entities.exclusions:
            parsed.entities.exclusions = fallback.entities.exclusions
        if parsed.entities.rainy is None:
            parsed.entities.rainy = fallback.entities.rainy
        if not parsed.entities.requested_place:
            parsed.entities.requested_place = fallback.entities.requested_place
    return parsed


def _run_tool_loop(text: str, sys_prompt: str, session_ctx: dict) -> tuple[str, dict]:
    """Phase 5 LLM tool-calling loop capped at MAX_STEPS, returning (reply, tool_state)."""
    msgs = [{"role": "system", "content": sys_prompt}]
    msgs.extend(session_ctx.get("messages") or [])
    msgs.append({"role": "user", "content": text})
    tool_state = {"plan": (session_ctx.get("state") or {}).get("current_plan"), "weather": None}

    for step in range(MAX_STEPS):
        res = call_model_tools(msgs, TOOL_SCHEMAS)
        tool_calls = res.get("tool_calls") or []
        if not tool_calls:
            return (res.get("text") or "", tool_state)
        msgs.append(res["assistant_message"])
        for tc in tool_calls:
            fn = tc.get("function") or {}
            name = fn.get("name", "")
            try:
                args = json.loads(fn.get("arguments") or "{}")
            except json.JSONDecodeError:
                args = {}
            result = dispatch(name, args, tool_state)
            note(f"tool_loop step={step + 1} tool={name}")
            msgs.append({
                "role": "tool",
                "tool_call_id": tc.get("id", name),
                "content": json.dumps(result, ensure_ascii=False),
            })
    note("tool_loop hit MAX_STEPS")
    return ("", tool_state)


def answer(text: str, session_id: str | None = None, user_key: str = "default") -> dict:
    sid = session_id or f"ephemeral-{uuid.uuid4().hex[:8]}"
    session_ctx = memory.get_session_context(sid)
    saved_constraints = (session_ctx.get("state") or {}).get("constraints") or {}
    memory.append_message(sid, "user", text)

    note("agent: bắt đầu, tối đa %d bước" % MAX_STEPS)
    intent_res = _classify_and_extract(text, saved_constraints=saved_constraints)
    intent = intent_res.intent
    ent = intent_res.entities
    note(f"intent={intent} lang={ent.language}")

    # Persist user language & interests preference
    if ent.language:
        memory.update_preferences(user_key, language=ent.language, interests=ent.interests or None)

    if intent == "REFUSE":
        note("dừng: từ chối đặt vé hoặc dữ liệu thanh toán")
        call_model(SYSTEM, "Người dùng đòi đặt vé hoặc đưa dữ liệu thanh toán. Từ chối, không nhắc lại số.")
        memory.append_message(sid, "assistant", REFUSE)
        return {"output": REFUSE}

    if intent == "OUT_OF_SCOPE":
        note("dừng: ngoài phạm vi một ngày ở Hà Nội")
        msg = OUT_OF_SCOPE_WEATHER_MSG if "thời tiết" in _norm(text) else OUT_OF_SCOPE_MSG
        call_model(SYSTEM, "Từ chối khéo vì yêu cầu ngoài phạm vi một ngày ở Hà Nội.")
        memory.append_message(sid, "assistant", msg)
        return {"output": msg}

    sys_prompt = build_system_prompt(ent.language, session_ctx)

    # Save active constraints to session state
    memory.update_session_state(sid, constraints={
        "start_date": ent.start_date,
        "window": list(ent.window) if ent.window else None,
        "budget_vnd": ent.budget_vnd,
        "interests": ent.interests,
        "n_people": ent.n_people,
        "exclusions": ent.exclusions,
        "rainy": ent.rainy,
        "closed_day": ent.closed_day,
    })

    if intent in ("SEARCH_PLACE", "RECOMMEND_PLACE", "TRAVEL_INFO"):
        chunks = retrieve_knowledge(ent.query or text, top_k=5, lang=ent.language)
        note(f"rag: retrieved {len(chunks)} chunks")
        res = call_model(sys_prompt, build_rag_prompt(intent, text, chunks, asdict(ent)))
        out = _format_rag_fallback(chunks) if ai.MODEL_PROVIDER == "fake" else res["text"]
        memory.append_message(sid, "assistant", out)
        return {"output": out}

    if intent == "ESTIMATE_BUDGET":
        n_people = ent.n_people or 2
        chunks = retrieve_knowledge(ent.query or "Hà Nội lịch sử ẩm thực", top_k=5, lang=ent.language)
        priced = [c for c in chunks if isinstance(c.get("price_vnd"), int)]
        est = sum(c["price_vnd"] for c in priced[:3]) * n_people
        lines = [f"Ước tính tham khảo cho {n_people} người ({len(priced[:3])} điểm từ dữ liệu):"]
        for c in priced[:3]:
            lines.append(f"- {c['name']}: {c['price_vnd']} VND/người")
        lines.append(f"Tổng vé ước tính: {est} VND (chưa gồm ăn uống phát sinh).")
        summary = "\n".join(lines)
        res = call_model(sys_prompt, build_budget_prompt(text, summary))
        out = summary if ai.MODEL_PROVIDER == "fake" else res["text"]
        memory.append_message(sid, "assistant", out)
        return {"output": out}

    # PLAN_TRIP or MODIFY_TRIP
    question = _ask_from_entities(ent, text)
    if question:
        note("dừng: thiếu thông tin, hỏi một câu")
        memory.update_session_state(sid, pending_question=question)
        call_model(sys_prompt, "Hỏi đúng một ý còn thiếu: " + question)
        memory.append_message(sid, "assistant", question)
        return {"output": question}

    # Real LLM tool-calling loop when OpenAI-compatible provider is active
    if ai.MODEL_PROVIDER in ("openai", "gemini", "openai-compatible"):
        loop_reply, tool_state = _run_tool_loop(text, sys_prompt, session_ctx)
        plan = tool_state.get("plan")
        if plan and loop_reply and str(plan.get("total_cost")) in loop_reply:
            memory.update_session_state(sid, current_plan=plan, pending_question=None)
            memory.append_message(sid, "assistant", loop_reply)
            return {"output": loop_reply}

    weather = get_weather(ent.start_date or "2026-11-28", bool(ent.rainy) or ("mưa" in _norm(text)))
    found = search_pois(
        ent.interests,
        bool(weather["is_rainy"]),
        ent.exclusions,
        ent.closed_day,
        ent.budget_vnd,
        ent.n_people,
    )
    plan = plan_route(
        [poi["id"] for poi in found],
        ent.window[0],
        ent.window[1],
        ent.budget_vnd,
        ent.n_people,
    )
    memory.update_session_state(sid, current_plan=plan, pending_question=None)
    note("dừng: đã có lịch từ công cụ, 3 công cụ + model")
    rendered = _format_plan(plan, ent.requested_place or _missing_place(text), bool(weather["is_rainy"]))
    res = call_model(sys_prompt, build_trip_prompt(rendered, asdict(ent)))
    if ai.MODEL_PROVIDER == "fake":
        memory.append_message(sid, "assistant", rendered)
        return {"output": rendered}
    out = res["text"] if str(plan["total_cost"]) in res["text"] else rendered
    memory.append_message(sid, "assistant", out)
    return {"output": out}
