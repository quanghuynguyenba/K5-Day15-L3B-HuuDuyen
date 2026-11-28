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
  số người, sở thích. CHỈ hỏi lại khi thiếu NGÂN SÁCH, và hỏi đúng MỘT câu ngắn. Thiếu thứ khác thì dùng mặc định
  (2 người, %s–%s, friends, sở thích lịch sử + văn hoá), lập lịch luôn và nói một câu đã giả định gì.
- TUYỆT ĐỐI không mô tả một lịch trình (số điểm, tổng tiền, thời gian) nếu chưa gọi plan_route trong lượt này hoặc
  không có current_plan — mọi lịch phải do plan_route tạo ra.
- Chỉ phục vụ du lịch HÀ NỘI. Ngoài phạm vi (đặt vé, thanh toán, thành phố khác…) thì từ chối ngắn và chỉ gợi ý việc
  bạn làm được ở Hà Nội; không đề nghị lập lịch thành phố khác.
- Lập lịch: gọi search_pois rồi plan_route với TẤT CẢ id search_pois trả về (solver tự chọn và xếp thứ tự,
  không tự lọc bớt). KHÔNG tự tính khoảng cách, giờ, tiền — chỉ dùng số plan_route trả về.
  Điểm trong "dropped" thì giải thích ngắn vì sao bỏ (hết giờ, vượt ngân sách, đóng cửa).
- Khách sửa lịch ("bỏ bảo tàng", "bớt 200k"): gọi lại tool với ràng buộc mới, dựa trên lịch hiện tại.
- Hỏi về mưa: gọi get_weather; is_rainy thì tìm lại với indoor_only=true cho khung giờ mưa.
- Nếu thời tiết unavailable hoặc is_rainy=null: nói chưa có dự báo, không kết luận không mưa. mock=true là dữ liệu minh họa, phải nói rõ.
- Khách báo đang ở đâu / bị trễ giữa chuyến: gọi plan_route cho phần còn lại của ngày với start_lat/start_lng
  = vị trí hiện tại, start_time = giờ hiện tại, bỏ các điểm đã đi.
- Có current_location (GPS) và khách không nói vị trí khác: dùng nó làm start_lat/start_lng. Khách nêu tên một nơi
  (vd "đang ở Hồ Gươm") thì ưu tiên nơi đó. Không đọc toạ độ cho khách.
- Khách nhắc một khu vực / địa danh (Sơn Tây, Ba Vì, Tây Hồ, phố cổ, Đường Lâm…): gọi search_pois với area = tên đó.
  CHỈ dùng điểm trong kết quả, KHÔNG thêm điểm ở nơi khác. area_info.note hoặc n_schedulable ít → nói thẳng dữ liệu
  khu vực này còn thiếu, kể tên điểm trong missing_data và thiếu gì; không lấp bằng điểm ở trung tâm.
  Không tìm được khu vực → hỏi lại khách. Không hứa "tìm thêm thông tin" ngoài dữ liệu — chỉ có các tool ở trên;
  có thể gợi ý khu vực lân cận có đủ dữ liệu (vd Ba Vì, Hoàn Kiếm) để khách chọn.
- Hỏi về một điểm (giờ mở, giá, lưu ý): LUÔN gọi lookup_poi trước, chỉ trả lời theo kết quả đó — KHÔNG dùng trí nhớ.
  Trường nào null hoặc không tìm thấy thì nói "chưa có dữ liệu", không đoán.
- budget_vnd trong trạng thái là ngân sách hiện tại do code giữ. Nếu replanned_by_code=true: lịch trong current_plan
  ĐÃ được tính lại bằng code theo ngân sách mới — KHÔNG gọi plan_route nữa, chỉ báo kết quả. Không tự cộng trừ tiền.
- Giao diện ĐÃ hiển thị lịch chi tiết (giờ, giá từng điểm) trên bản đồ và timeline. Sau khi lập / sửa lịch, trả lời
  NGẮN tối đa 4 câu: số điểm, tổng tiền, tổng thời gian, điểm bị bỏ kèm lý do. Không liệt kê lại từng điểm trừ khi
  khách hỏi. CHÉP ĐÚNG các số trong plan_summary / summary (n_stops, total_cost_vnd, total_time, dropped) —
  không tự đếm, không tự cộng. Lý do bỏ điểm trong dữ liệu viết tiếng Việt — dịch sang ngôn ngữ trả lời.
""" % (DEFAULT_START_TIME, DEFAULT_END_TIME)

LANG_NAMES = {"vi": "tiếng Việt", "en": "English", "ko": "한국어 (tiếng Hàn)", "ja": "日本語 (tiếng Nhật)",
              "zh": "中文 (tiếng Trung giản thể)"}

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
    from agent.tools import TOOL_SCHEMAS, dispatch, dumps, plan_summary
    lang = session_lang(user_text, state)
    plan_before = state.get("plan")
    replanned = apply_budget_from_text(user_text, state)
    named = apply_named_start(user_text, state)  # "Tôi đang ở Hồ Gươm" → code đặt điểm xuất phát
    removed = apply_exclusion_from_text(user_text, state)  # "bỏ Văn Miếu" → code loại điểm + lập lại lịch
    replanned = replanned or bool(removed)
    loc = state.get("location")
    ctx = {"date": state.get("date"),
           "reply_language": lang,
           "budget_vnd": state.get("budget_vnd"),
           "replanned_by_code": replanned,
           "start_from_code": named and {"name": named["name"], "lat": named["lat"], "lng": named["lng"],
                                         "note": "khách vừa nói đang ở đây — lập lịch xuất phát từ điểm này"},
           "current_location": loc and {"lat": loc["lat"], "lng": loc["lng"], "source": "GPS của khách",
                                        "accuracy_m": loc.get("accuracy")},
           "plan_summary": state.get("plan") and plan_summary(state["plan"]),
           "current_plan": state.get("plan") and
           {k: v for k, v in state["plan"].items() if k != "polyline"}}
    msgs = [{"role": "system", "content": SYSTEM + "\nTrạng thái hiện tại: " + dumps(ctx)}]
    msgs += state["history"][-10:]
    msgs.append({"role": "user", "content": user_text})
    if replanned:  # đưa thẳng câu kết quả — model chỉ diễn đạt lại, không phải đọc JSON / lịch sử cũ
        msgs.append({"role": "system", "content": "Lịch VỪA được tính lại bằng code. %sKết quả: %s Diễn đạt lại "
                     "đúng nội dung này, giữ nguyên mọi con số." % (
                         "Đã bỏ theo yêu cầu: %s. " % ", ".join(removed) if removed else "",
                         facts_sentence(plan_summary(state["plan"]), "vi", state.get("budget_vnd")))})
    # Nhắc ngôn ngữ ở CUỐI hội thoại — prompt hệ thống viết tiếng Việt nên model hay trả lời tiếng Việt
    msgs.append({"role": "system", "content": "Trả lời HOÀN TOÀN bằng %s, ngắn gọn tối đa 4 câu, KHÔNG liệt kê "
                 "lại từng điểm (giao diện đã hiển thị). Tên địa điểm kèm tên tiếng Việt trong ngoặc."
                 % LANG_NAMES.get(lang, lang)})
    client = _get_client()
    # Code đã lập lại lịch (bớt / thêm ngân sách) → không đưa tool: model chỉ báo kết quả, không gọi
    # plan_route lần nữa với danh sách điểm thu hẹp (lỗi "thêm tiền mà không thêm điểm").
    tools = None if replanned else TOOL_SCHEMAS
    used = []

    def run(force_tool: bool):
        for step in range(MAX_STEPS):
            kw = {"model": LLM_MODEL, "messages": msgs}
            if tools:
                kw["tools"] = tools
                if force_tool and step == 0:
                    kw["tool_choice"] = "required"
            m = client.chat.completions.create(**kw).choices[0].message
            if not m.tool_calls:
                return m.content or ""
            msgs.append(m.model_dump(exclude_none=True))
            for tc in m.tool_calls:
                used.append(tc.function.name)
                try:
                    result = dispatch(tc.function.name, json.loads(tc.function.arguments or "{}"), state)
                except Exception as e:  # trả lỗi cho LLM thay vì làm sập app
                    result = {"error": str(e)}
                msgs.append({"role": "tool", "tool_call_id": tc.id, "content": dumps(result)})
        return None

    state["hallucination_blocked"] = False
    reply = run(force_tool=False)
    # Chặn bịa lịch: model mô tả một lịch (số điểm / tiền) mà KHÔNG gọi tool nào và không khớp lịch đang có
    # → chạy lại, buộc gọi tool. Vẫn không ra lịch thật → không trả câu bịa, hỏi ngân sách.
    if reply is not None and not used and not replanned and claims_itinerary(reply):
        current = state.get("plan")
        if not (current and numbers_match(reply, plan_summary(current))):
            state["hallucination_blocked"] = True
            reply = run(force_tool=True)
            if state.get("plan") is plan_before and (reply is None or claims_itinerary(reply)):
                return NO_PLAN_REPLY.get(lang, NO_PLAN_REPLY["en"])
    if reply is None:
        return "Xin lỗi, tôi chưa xếp xong lịch trình. Bạn thử nói lại ngắn hơn nhé."
    # Chốt chặn cuối: lịch đổi trong lượt này mà câu trả lời không chứa ĐÚNG số điểm + tổng tiền → thay bằng câu
    # viết sẵn từ số liệu code (đúng ngôn ngữ). Khách không bao giờ thấy số do model đếm / cộng sai.
    plan = state.get("plan")
    if plan is not None and plan is not plan_before:
        ps = plan_summary(plan)
        if not numbers_match(reply, ps):
            state["reply_replaced"] = True
            return facts_sentence(ps, lang, state.get("budget_vnd"))
    state["reply_replaced"] = False
    return reply


NO_PLAN_REPLY = {
    "vi": "Mình chưa lập được lịch trình — bạn cho mình biết ngân sách dự kiến nhé?",
    "en": "I couldn't build an itinerary yet — what is your budget?",
    "ko": "아직 일정을 만들지 못했습니다. 예산이 얼마인가요?",
    "ja": "まだ旅程を作成できていません。ご予算はいくらですか？",
    "zh": "还没能生成行程——您的预算是多少？",
}
_STOP_WORDS = r"(?:điểm|địa điểm|chỗ|stops?|places?|attractions?|곳|군데|か所|カ所|ヶ所|个地点|个景点|处)"


def claims_itinerary(reply: str) -> bool:
    """Câu trả lời có mô tả một lịch trình cụ thể không (vd "4 điểm", "6곳", "5 stops")."""
    return bool(re.search(r"\d+\s*" + _STOP_WORDS, reply.lower()))


def apply_named_start(text: str, state: dict) -> dict | None:
    """"Tôi đang ở Hồ Gươm" / "mình ở phố cổ" / "I'm at Hoan Kiem lake" → tra địa danh (tên POI, rồi khu vực TomTom)
    và ghi state["named_start"] — default_start() dùng điểm này thay GPS. Không nhận ra địa danh → None."""
    from agent.tools import lookup_poi, resolve_area
    state["named_start_turn"] = False
    m = re.search(r"(?:đang\s+ở|tôi\s+ở|mình\s+ở|em\s+ở|chúng\s+tôi\s+ở|i'?m\s+(?:now\s+)?at|i\s+am\s+at|we'?re\s+at|"
                  r"now\s+at|currently\s+at)\s+(.+?)(?=\s*(?:[,.;!?]|\s(?:trễ|muộn|rồi|late|now|and|và)\b|$))",
                  text, re.IGNORECASE)
    if not m:
        return None
    from agent.tools import _fold
    from rag.search import get_poi, load_pois
    place = m.group(1).strip()
    q = _fold(place)
    # Thứ tự: (1) tên POI  (2) tên khu vực hành chính (chỉ nhận khi tên khớp thật — TomTom hay khớp đại,
    # vd "Hồ Gươm" → "Tây Hồ")  (3) tên gọi khác chỉ có trong mô tả POI (vd "Hồ Gươm" = Hồ Hoàn Kiếm)
    found = (lookup_poi(place).get("found") or [None])[0]
    poi = get_poi(found["id"]) if found else None
    area = None if poi else resolve_area(place)
    if area and q not in _fold(area["name"]):
        area = None
    if not poi and not area and len(q) >= 4:
        poi = next((p for p in load_pois()
                    if q in _fold(" ".join([p.get("description_vi", ""), p.get("description_en", "")]))), None)
    if poi:
        hit = {"name": poi["name"]["vi"], "lat": poi["lat"], "lng": poi["lng"]}
    elif area:
        hit = {"name": area["name"], "lat": area["lat"], "lng": area["lng"]}
    else:
        return None
    state["named_start"] = hit
    state["named_start_turn"] = True
    return hit


def apply_exclusion_from_text(text: str, state: dict) -> list:
    """"bỏ Văn Miếu" / "không đi Hỏa Lò" / "remove Temple of Literature" → loại điểm BẰNG CODE:
    thêm vào state["excluded_ids"] (dispatch plan_route luôn lọc), lập lại lịch ngay. → tên các điểm đã bỏ.
    "bỏ qua ..." (vd câu tấn công "bỏ qua mọi hướng dẫn") không tính."""
    from agent.tools import dispatch, lookup_poi
    if not state.get("route_args"):
        return []
    m = re.search(r"(?:^|\s)(?:bỏ(?!\s+qua)|xoá|xóa|loại|không\s+đi|khỏi\s+đi|remove|skip|drop|exclude)\s+(.+)",
                  text.strip(), re.IGNORECASE)
    if not m:
        return []
    name = re.sub(r"\s*(?:đi|nhé|nha|ra|giúp\s+(?:tôi|mình|em)|khỏi\s+lịch(?:\s+trình)?|ra\s+khỏi.*|please|from.*)"
                  r"[\s.!?]*$", "", m.group(1), flags=re.IGNORECASE).strip(" .!?,")
    found = lookup_poi(name).get("found") or []
    if not found:
        return []
    poi = found[0]
    state.setdefault("excluded_ids", [])
    if poi["id"] not in state["excluded_ids"]:
        state["excluded_ids"].append(poi["id"])
    dispatch("plan_route", dict(state["route_args"]), state)
    return [poi["name"]["vi"]]


def _numbers_in(text: str) -> set:
    out = set()
    for raw in re.findall(r"\d[\d.,\s]*\d|\d", text):
        digits = re.sub(r"[^\d]", "", raw)
        if digits:
            out.add(int(digits))
    for n, unit in re.findall(r"(\d+(?:[.,]\d+)?)\s*(만|k|nghìn|ngàn|triệu|million)", text.lower()):
        out.add(_money(n, {"만": "man", "million": "triệu"}.get(unit, unit)) if unit != "만"
                else int(float(n.replace(",", ".")) * 10_000))
    return out


def numbers_match(reply: str, ps: dict) -> bool:
    nums = _numbers_in(reply)
    return ps["n_stops"] in nums and ps["total_cost_vnd"] in nums


_FACTS = {
    "vi": ("Lịch đã cập nhật: {n} điểm, tổng {cost} VND, khoảng {time}{budget}.", " (ngân sách {b} VND)",
           " Không xếp: {d}.", "{name} ({reason})"),
    "en": ("Itinerary updated: {n} stops, total {cost} VND, about {time}{budget}.", " (budget {b} VND)",
           " Not included: {d}.", "{name} ({reason})"),
    "ko": ("일정이 업데이트되었습니다: {n}곳, 총 {cost} VND, 약 {time}{budget}.", " (예산 {b} VND)",
           " 제외: {d}.", "{name} ({reason})"),
    "ja": ("旅程を更新しました：{n}か所、合計 {cost} VND、約 {time}{budget}。", "（予算 {b} VND）",
           " 除外：{d}。", "{name}（{reason}）"),
    "zh": ("行程已更新：{n} 个地点，总计 {cost} VND，约 {time}{budget}。", "（预算 {b} VND）",
           " 未安排：{d}。", "{name}（{reason}）"),
}
_TIME = {"vi": "{h} giờ {m} phút", "en": "{h} h {m} min", "ko": "{h}시간 {m}분", "ja": "{h}時間{m}分", "zh": "{h}小时{m}分钟"}


def facts_sentence(ps: dict, lang: str, budget: int | None = None) -> str:
    """Câu tóm tắt viết sẵn từ số liệu code. Tên địa điểm giữ tiếng Việt; lý do bỏ giữ tiếng Việt cho ngắn gọn."""
    main, bud, drop, item = _FACTS.get(lang, _FACTS["en"])
    h, m = re.findall(r"\d+", ps["total_time"])[:2]
    text = main.format(n=ps["n_stops"], cost=f"{ps['total_cost_vnd']:,}",
                       time=_TIME.get(lang, _TIME["en"]).format(h=h, m=m),
                       budget=bud.format(b=f"{budget:,}") if budget else "")
    if ps["dropped"]:
        text += drop.format(d=", ".join(item.format(**d) for d in ps["dropped"][:4]))
    return text


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


def session_lang(text: str, state: dict) -> str:
    """Ngôn ngữ trả lời của phiên. Câu có chữ của một ngôn ngữ rõ ràng thì đổi theo; câu không có chữ
    (vd "OK", "200k", số) giữ ngôn ngữ trước đó — tránh khách Hàn gõ "OK" bị trả lời tiếng Anh."""
    detected = detect_lang(text)
    letters = re.sub(r"[^a-zA-Z]", "", text)
    if detected != "en" or len(letters) >= 4 or "lang" not in state:
        state["lang"] = detected
    return state["lang"]


_UNITS = {"triệu": 1_000_000, "tr": 1_000_000, "m": 1_000_000, "k": 1_000, "nghìn": 1_000, "ngàn": 1_000,
          "đ": 1, "vnd": 1, "đồng": 1}


def _money(num: str, unit: str) -> int:
    n = float(num.replace(",", "."))
    return int(n * _UNITS.get(unit, 1))


def budget_absolute(text: str) -> int | None:
    """Khách nêu ngân sách mới (không phải bớt / thêm): "1 triệu", "800k", "100만동", "1.000.000đ", "1 million"."""
    t = text.lower()
    if re.search(r"(bớt|giảm|cắt|thêm|tăng|reduce|cut|lower|add|increase|raise)\s*(?:đi|lên|xuống|by)?\s*\d", t):
        return None
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*만\s*(?:동|vnd)?", t)
    if m:
        return int(float(m.group(1).replace(",", ".")) * 10_000)
    m = re.search(r"(\d+)\s*(?:triệu|tr)\s*(rưỡi|\d)(?!\d)", t)  # "1 triệu rưỡi", "1tr5"
    if m:
        extra = 500_000 if m.group(2) == "rưỡi" else int(m.group(2)) * 100_000
        return int(m.group(1)) * 1_000_000 + extra
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*(million|triệu|tr|nghìn|ngàn|k)\b", t)
    if m:
        unit = "triệu" if m.group(2) == "million" else m.group(2)
        return _money(m.group(1), unit)
    m = re.search(r"\b(\d{1,3}(?:[.,]\d{3})+|\d{5,})\s*(?:đ|vnd|đồng|dong|₫)", t)
    if m:
        return int(re.sub(r"[.,]", "", m.group(1)))
    return None


def apply_budget_from_text(text: str, state: dict) -> bool:
    """Ngân sách do CODE giữ trong state["budget_vnd"] (dispatch plan_route luôn dùng số này).
    "bớt / thêm X" khi đã có lịch → tính ngân sách mới và LẬP LẠI LỊCH NGAY bằng code. → True nếu đã lập lại."""
    from agent.tools import dispatch
    absolute = budget_absolute(text)
    if absolute is not None:
        state["budget_vnd"] = absolute
        return False
    new = budget_change(text, state.get("budget_vnd"))
    if new is None:
        return False
    state["budget_vnd"] = new
    args = state.get("route_args")
    if args:
        dispatch("plan_route", dict(args), state)
        return True
    return False


def budget_change(text: str, current: int | None) -> int | None:
    """"bớt 200k" / "giảm 0.5 triệu" / "thêm 300k" / "cut 200k" → ngân sách mới tính bằng code (không để LLM
    tự cộng trừ). current = ngân sách của lần lập lịch trước. Không có câu tăng/giảm hoặc chưa có lịch → None."""
    if current is None:
        return None
    m = re.search(r"(bớt|giảm|cắt|thêm|tăng|reduce|cut|lower|add|increase|raise)\s*(?:đi|lên|xuống|by)?\s*"
                  r"(\d+(?:[.,]\d+)?)\s*(triệu|tr|k|nghìn|ngàn|đồng|đ|vnd|m)\b", text.lower())
    if not m:
        return None
    delta = _money(m.group(2), m.group(3))
    sign = 1 if m.group(1) in ("thêm", "tăng", "add", "increase", "raise") else -1
    return max(0, int(current) + sign * delta)


def _chat_mock(text: str, state: dict) -> str:
    from agent.tools import dispatch
    from rag.search import get_poi
    t = text.lower()
    c = state["constraints"]
    c.setdefault("budget_vnd", 1_000_000)
    c.setdefault("n_people", 2)
    c.setdefault("interests", ["history"])
    c.setdefault("start_time", DEFAULT_START_TIME)
    from agent.tools import default_start
    c["start"] = default_start(state)  # GPS của khách nếu có, không thì Hồ Gươm
    c["lang"] = detect_lang(text)

    changed = budget_change(text, c["budget_vnd"])
    if changed is not None:
        c["budget_vnd"] = changed
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

    state["budget_vnd"] = c["budget_vnd"]  # ngân sách do code giữ — dispatch plan_route đọc số này
    pois = dispatch("search_pois", {"interests": c["interests"] + ["food"], "group_type": "friends",
                                    "max_price": c["budget_vnd"], "indoor_only": indoor}, state)
    plan = dispatch("plan_route", {"poi_ids": [p["id"] for p in pois], "start_lat": c["start"][0],
                                   "start_lng": c["start"][1], "start_time": c["start_time"],
                                   "budget_vnd": c["budget_vnd"], "n_people": c["n_people"]}, state)
    lines = ["[MOCK — chưa nối LLM] lang=%s · %d người · ngân sách %s VND%s" % (
        c["lang"], c["n_people"], f"{c['budget_vnd']:,}", " · chỉ điểm trong nhà" if indoor else "")]
    w = state.get("weather") or {}
    if re.search(r"mưa|rain|비|雨", t) and w.get("is_rainy") is not None:
        lines.append("Thời tiết %s: %s (xác suất mưa cao nhất %s%%)." % (
            w.get("date") or state.get("date"), "có mưa → ưu tiên điểm trong nhà" if w["is_rainy"]
            else "dự báo không mưa → giữ lịch", max((w.get("rain_prob_by_hour") or {0: "?"}).values())))
    if (state.get("weather") or {}).get("status") == "unavailable":
        lines.append("Thời tiết: chưa có dự báo — " + state["weather"].get("error", "vui lòng thử lại sau"))
    if (state.get("weather") or {}).get("mock"):
        lines.append("Thời tiết đang dùng dữ liệu MẪU, không phải dự báo thật.")
    for i, s in enumerate(plan["stops"], 1):
        lines.append("%d. %s–%s %s (%s VND)" % (i, s["arrive"], s["depart"],
                                                 get_poi(s["poi_id"])["name"]["vi"], f"{s['cost']:,}"))
    lines.append("Tổng: %s VND · %d phút" % (f"{plan['total_cost']:,}", plan["total_minutes"]))
    if plan["dropped"]:
        lines.append("Bỏ: " + ", ".join(plan["dropped"]))
    return "\n".join(lines)
