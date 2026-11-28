"""Huy — đăng ký tool cho LLM + chuyển lời gọi tool sang các module.

TOOL_SCHEMAS: định dạng tool của OpenAI Chat Completions (Gemini OpenAI-compatible dùng chung được).
dispatch(): chạy tool theo tên, lưu kết quả quan trọng vào state (vd lịch trình hiện tại).
"""
import json

from config import DEFAULT_END_TIME, DEFAULT_START, DEFAULT_START_TIME, USE_MOCK
from rag.search import get_poi, get_poi_context, search_pois
from routing.optimizer import plan_route
from services.tts import get_audio_result, load_prepared_audio, validate_language
from services.content import has_source, is_placeholder
from services.weather import get_weather

GROUP_TYPES = ["family", "elderly", "couple", "friends", "solo"]

TOOL_SCHEMAS = [
    {"type": "function", "function": {
        "name": "lookup_poi",
        "description": "Tra cứu một địa điểm theo tên (Việt / Anh, có hoặc không dấu): giá vé, giờ mở, ngày nghỉ, "
                       "lưu ý, mô tả. BẮT BUỘC gọi trước khi nói về giá / giờ / lưu ý của một điểm.",
        "parameters": {"type": "object", "properties": {
            "name": {"type": "string", "description": "tên địa điểm khách hỏi, vd 'Văn Miếu'"},
        }, "required": ["name"]}}},
    {"type": "function", "function": {
        "name": "search_pois",
        "description": "Tìm điểm tham quan ở Hà Nội đã lọc theo giá vé/người, nhóm khách, trong nhà, ngày đóng cửa. "
                       "Khách nhắc một khu vực / địa danh (Sơn Tây, Ba Vì, Tây Hồ, phố cổ, Đường Lâm…) thì PHẢI truyền "
                       "area — kết quả chỉ gồm điểm trong khu vực đó, kèm area_info về độ đủ dữ liệu.",
        "parameters": {"type": "object", "properties": {
            "area": {"type": "string", "description": "tên khu vực / địa danh khách nhắc, vd 'Sơn Tây'"},
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

NARRATE_LANGS = {"vi": "tiếng Việt", "en": "English", "ko": "한국어 (tiếng Hàn)", "ja": "日本語 (tiếng Nhật)",
                 "zh": "简体中文 (tiếng Trung giản thể)"}
NARRATE_SYSTEM = ("Bạn là hướng dẫn viên du lịch đang nói với du khách tại chỗ. Viết lời thuyết minh 60–90 giây, "
                  "VIẾT TOÀN BỘ bằng %s (kể cả khi nội dung được cung cấp là tiếng Việt / tiếng Anh — hãy dịch). "
                  "CHỈ dùng nội dung được cung cấp, không bịa năm, số liệu hay giai thoại. "
                  "Phần ghi chú có câu dành cho người làm dữ liệu (toạ độ, nguồn, kiểm chứng, gợi ý thời lượng, "
                  "nhóm khách, \"bản ghi kế thừa\"…) — KHÔNG đọc những câu đó; chỉ giữ thông tin có ích cho khách "
                  "(giá vé, giờ mở, lưu ý khi tham quan). Không xưng là ban quản lý địa điểm. Nhắc tên địa điểm, "
                  "kèm tên tiếng Việt gốc; không tự phiên âm tên riêng sang chữ khác. Nói như hướng dẫn viên tại chỗ: "
                  "không nhắc tới bản đồ, toạ độ, dữ liệu, nguồn hay việc 'chưa kiểm chứng'; nếu thiếu giờ / giá thì "
                  "chỉ khuyên khách hỏi tại chỗ.")


def narrate_system(lang: str) -> str:
    return NARRATE_SYSTEM % NARRATE_LANGS.get(lang, lang)


class NarrationCancelled(Exception):
    """Người dùng đã huỷ (đóng popup) — dừng, không gọi TTS, không ghi file."""


def _check(cancel):
    if cancel is not None and cancel.is_set():
        raise NarrationCancelled()


def narrate(poi_id: str, lang: str, cancel=None) -> dict:
    """cancel: threading.Event tuỳ chọn. Được set khi client ngắt kết nối → dừng ở điểm kiểm tra kế tiếp
    (trước khi gọi LLM, trước khi gọi TTS). Lời gọi LLM đang chạy dở không ngắt được, nhưng kết quả bị bỏ."""
    from agent.llm import call_llm  # import trễ để tránh vòng import
    validate_language(lang)
    ctx = get_poi_context(poi_id, lang)
    if not ctx:
        return {"text": "", "audio_path": None}
    prepared = load_prepared_audio(poi_id, lang, ctx)
    if prepared:
        return prepared
    poi = get_poi(poi_id) or {}
    if is_placeholder(ctx) or not has_source(poi.get("source")):
        return {"text": "Chưa có nội dung địa điểm và nguồn đã kiểm tra để tạo thuyết minh.",
                "audio_path": None, "mock": True, "source": "placeholder", "tts_status": "not_ready",
                "warning": "Cần bổ sung mô tả có nguồn hoặc kịch bản demo đã duyệt."}
    if USE_MOCK:
        return {"text": "[MOCK — chưa nối LLM] " + ctx, "audio_path": None, "mock": True,
                "source": "mock", "tts_status": "disabled",
                "warning": "Chưa có model dịch/viết thuyết minh. Có thể dùng audio đã chuẩn bị và duyệt trước."}
    _check(cancel)
    named = "Địa điểm: %s (%s)\n%s" % (poi.get("name", {}).get("vi", poi_id), poi.get("name", {}).get("en", ""), ctx)
    text = call_llm(narrate_system(lang), named)  # có tên điểm — model gọi đúng tên, giữ tên tiếng Việt
    if not isinstance(text, str) or not text.strip():
        raise ValueError("Model chưa trả về nội dung thuyết minh.")
    _check(cancel)  # huỷ trong lúc LLM đang viết → không tạo audio
    try:
        audio = get_audio_result(poi_id, lang, text)
    except OSError:
        audio = {"audio_path": None, "tts_status": "unavailable",
                 "warning": "Chưa lưu được audio. Bạn vẫn có thể đọc nội dung thuyết minh."}
    return {"text": text, "mock": False, "source": "rag-llm", **audio}


def default_start(state: dict) -> tuple:
    """Điểm xuất phát khi khách không nói vị trí khác:
    - đang lập lịch cho một khu vực (vd Sơn Tây): GPS nếu khách đang ở trong khu vực đó, không thì trung tâm khu vực
    - còn lại: GPS của khách (server đã kiểm nằm trong vùng Hà Nội), không có thì Hồ Gươm."""
    loc, area, named = state.get("location"), state.get("area"), state.get("named_start")
    if named:  # khách tự nói "tôi đang ở X" — tin lời khách hơn GPS / khu vực
        return (named["lat"], named["lng"])
    if area:
        if loc and in_area(loc["lat"], loc["lng"], area, use_admin=False):  # GPS đổi liên tục — không tra quận
            return (loc["lat"], loc["lng"])
        return (area["lat"], area["lng"])
    return (loc["lat"], loc["lng"]) if loc else DEFAULT_START


# 30 quận / huyện / thị xã của Hà Nội trước đợt sắp xếp 2025. TomTom còn trả tên này cho một phần POI; phần khác đã
# theo tên phường / xã mới (vd "Cửa Nam", "Văn Miếu-Quốc Tử Giám") — với phần đó phải dùng khung bao.
OLD_DISTRICTS = {_d for _d in (
    "Hoàn Kiếm", "Ba Đình", "Tây Hồ", "Đống Đa", "Hai Bà Trưng", "Cầu Giấy", "Thanh Xuân", "Hoàng Mai", "Long Biên",
    "Nam Từ Liêm", "Bắc Từ Liêm", "Từ Liêm", "Hà Đông", "Sơn Tây", "Ba Vì", "Phúc Thọ", "Đan Phượng", "Hoài Đức",
    "Quốc Oai", "Thạch Thất", "Chương Mỹ", "Thanh Oai", "Thường Tín", "Phú Xuyên", "Ứng Hòa", "Mỹ Đức", "Thanh Trì",
    "Gia Lâm", "Đông Anh", "Sóc Sơn", "Mê Linh")}


def in_area(lat: float, lng: float, area: dict, use_admin: bool = True, name: str = "",
            district: str | None = None) -> bool:
    """Điểm có thuộc khu vực không. Thứ tự:
    (0) POI có trường "district" trong pois.json (quận / huyện, do nhóm dữ liệu điền) → so đúng tên, chắc chắn nhất;
    (1) tên POI chứa tên khu vực khách nói (vd "Vườn quốc gia Ba Vì" ∈ "Ba Vì");
    (2) POI còn mang tên quận / huyện CŨ (reverse geocode, có cache) → so đúng tên quận với khu vực;
    (3) còn lại (tên phường mới / không rõ) → khung bao của khu vực; (4) không có khung → vòng tròn quanh tâm."""
    from routing.maps import _haversine_km, poi_admin
    q = _fold(area.get("query") or "")
    if district and area.get("level") == "municipality" and area.get("admin"):
        return _fold(district) == _fold(area["admin"]) or bool(q and q in _fold(name))
    if name and q and q in _fold(name):
        return True
    if use_admin and area.get("level") == "municipality" and area.get("admin") in OLD_DISTRICTS:
        adm = poi_admin(lat, lng)
        if adm and adm.get("municipality") in OLD_DISTRICTS:
            return _fold(adm["municipality"]) == _fold(area["admin"])
    box = area.get("bbox")
    if box:
        return box[0] <= lat <= box[2] and box[1] <= lng <= box[3]
    return _haversine_km((lat, lng), (area["lat"], area["lng"])) <= area["radius_km"]


def resolve_area(name: str) -> dict | None:
    """Tên khu vực → {"name", "lat", "lng", "radius_km", "source"}.
    1) Đơn vị hành chính qua TomTom (Sơn Tây, Ba Vì, Tây Hồ…)  2) Tên một POI có sẵn (Đường Lâm, phố cổ…), bán kính 3 km."""
    from rag.search import load_pois
    from routing.maps import geocode
    g = geocode(name)
    if g:
        return {**g, "source": "tomtom", "query": name}
    q = _fold(name)
    for p in load_pois():
        if q and q in _fold(p["name"].get("vi", "") + " " + p["name"].get("en", "")):
            return {"name": p["name"]["vi"], "lat": p["lat"], "lng": p["lng"], "radius_km": 1.5, "source": "poi",
                    "query": name}
    return None


def search_in_area(args: dict, date: str | None, state: dict) -> dict:
    """search_pois giới hạn trong khu vực. Không loại điểm vì lệch sở thích (khu vực ít điểm) — chỉ xếp hạng.
    area_info nói thẳng khu vực có bao nhiêu điểm, bao nhiêu xếp lịch được, điểm nào thiếu dữ liệu."""
    from rag.search import is_schedulable, load_pois
    from routing.maps import _haversine_km
    area = resolve_area(args["area"])
    state["area"] = area
    if not area:
        return {"pois": [], "area_info": {"query": args["area"], "found": False,
                "note": "Không xác định được khu vực này ở Hà Nội — hỏi lại khách, không tự chọn nơi khác."}}
    def dist(p):
        return _haversine_km((p["lat"], p["lng"]), (area["lat"], area["lng"]))
    inside = [p for p in load_pois()
              if in_area(p["lat"], p["lng"], area, name=p["name"].get("vi", ""), district=p.get("district"))]
    ok = {p["id"] for p in search_pois([], args.get("group_type", "friends"), int(args.get("max_price", 10**9)),
                                       bool(args.get("indoor_only", False)), 200, date)}
    interests = {i.lower() for i in args.get("interests", [])}
    picked = sorted((p for p in inside if p["id"] in ok),
                    key=lambda p: (-len(interests & set(p.get("tags", []) + [p.get("category")])), dist(p)))
    missing = [{"name": p["name"]["vi"], "missing": [f for f, bad in (("giá vé", p.get("price_vnd") is None),
                ("giờ mở cửa", not p.get("open") or not p.get("close"))) if bad]}
               for p in inside if not is_schedulable(p)]
    return {"pois": [_slim_poi(p) for p in picked[:int(args.get("top_k", 15))]],
            "area_info": {"query": args["area"], "found": True, "name": area["name"], "radius_km": area["radius_km"],
                          "n_in_area": len(inside), "n_schedulable": len(picked), "missing_data": missing,
                          "note": None if len(picked) >= 3 else
                          "Dữ liệu khu vực này còn ít điểm xếp lịch được — nói rõ với khách, KHÔNG thêm điểm nơi khác."}}


REASON_VI = {"not_found": "không có dữ liệu", "missing_data": "thiếu giá / giờ mở cửa", "closed": "đóng cửa ngày đi",
             "budget": "vượt ngân sách", "time": "không kịp giờ", "low_priority": "hết thời gian trong ngày"}


def plan_summary(plan: dict) -> dict:
    """Số liệu tóm tắt TÍNH BẰNG CODE để LLM chép lại — model hay đếm / cộng sai khi tự đọc danh sách điểm."""
    from rag.search import get_poi
    stops = plan.get("stops", [])
    minutes = int(plan.get("total_minutes") or 0)
    reasons = plan.get("dropped_reasons") or {}
    dropped = [{"name": (get_poi(i) or {}).get("name", {}).get("vi", i),
                "reason": REASON_VI.get(reasons.get(i), reasons.get(i))}
               for i in plan.get("dropped", []) if reasons.get(i) not in ("not_found", "missing_data")]
    return {"n_stops": len(stops),
            "total_cost_vnd": int(plan.get("total_cost") or 0),
            "total_time": "%d giờ %d phút" % (minutes // 60, minutes % 60),
            "first_arrive": stops[0]["arrive"] if stops else None,
            "last_depart": stops[-1]["depart"] if stops else None,
            "stop_names": [(get_poi(s["poi_id"]) or {}).get("name", {}).get("vi", s["poi_id"]) for s in stops],
            "dropped": dropped}


def route_facts(plan: dict, state: dict) -> dict | None:
    """Chỉ đường tới điểm đến khách hỏi + khoảng cách các điểm gợi ý tới điểm neo — tính bằng code."""
    from rag.search import get_poi
    from routing.maps import _haversine_km
    from routing.validate import to_min
    dest, anchor = state.get("destination_id"), state.get("anchor")
    stops = plan.get("stops") or []
    if not (dest or anchor) or not stops:
        return None
    out = {}
    if dest and stops[0]["poi_id"] == dest:
        start_t = to_min((state.get("route_args") or {}).get("start_time") or DEFAULT_START_TIME)
        out["destination"] = {"name": get_poi(dest)["name"]["vi"], "arrive": stops[0]["arrive"],
                              "minutes_from_start": to_min(stops[0]["arrive"]) - start_t,
                              "from": state.get("start_label") or "vị trí của bạn",
                              "map": "đường đi đã vẽ trên bản đồ (TomTom)"}
    elif dest:
        out["destination"] = {"name": get_poi(dest)["name"]["vi"], "note": "không xếp được — xem dropped"}
    if anchor:
        out["nearby"] = [{"name": get_poi(s["poi_id"])["name"]["vi"],
                          "km_from_" + anchor["name"]: round(_haversine_km(
                              (get_poi(s["poi_id"])["lat"], get_poi(s["poi_id"])["lng"]), (anchor["lat"], anchor["lng"])), 1)}
                         for s in stops if s["poi_id"] != dest]
    return out


def search_near(args: dict, date: str | None, state: dict, radius_km: float = 2.5) -> list:
    """Gợi ý quanh điểm neo: ứng viên đã lọc (giá, nhóm, trong nhà, ngày) xếp theo khoảng cách tới điểm neo;
    chỉ lấy trong radius_km, thiếu thì nới dần. Điểm khách chỉ đích danh luôn đứng đầu."""
    from rag.search import get_poi
    from routing.maps import _haversine_km
    a = state["anchor"]
    pool = search_pois([], args.get("group_type", "friends"), int(args.get("max_price", 10**9)),
                       bool(args.get("indoor_only", False)), 200, date)
    dist = {p["id"]: _haversine_km((p["lat"], p["lng"]), (a["lat"], a["lng"])) for p in pool}
    # model hay đặt top_k = đúng số khách xin → thiếu chỗ cho điểm bắt buộc / điểm không kịp giờ: code lấy dư
    want = max(int(args.get("top_k", 15)), (state.get("max_stops") or 0) + 4)
    near = []
    for r in (radius_km, radius_km * 2, radius_km * 4):
        near = sorted((p for p in pool if dist[p["id"]] <= r), key=lambda p: dist[p["id"]])
        if len(near) >= min(want, 6):
            break
    must = [get_poi(i) for i in (state.get("must_ids") or []) if get_poi(i)]
    ids = {p["id"] for p in must}
    out = [_slim_poi(p) for p in must + [p for p in near if p["id"] not in ids]][:want]
    state["last_search_ids"] = [p["id"] for p in out]
    return out


def _fold(text: str) -> str:
    import unicodedata
    text = unicodedata.normalize("NFD", (text or "").lower().replace("đ", "d"))
    return " ".join("".join(ch for ch in text if unicodedata.category(ch) != "Mn").replace("–", " ").split())


def lookup_poi(name: str, limit: int = 3) -> dict:
    """Tìm POI theo tên (bỏ dấu, không phân biệt hoa thường). Giá / giờ thiếu thì trả None — không đoán."""
    from rag.search import load_pois
    q = _fold(name)
    if not q:
        return {"found": [], "note": "Chưa có tên địa điểm."}
    words = set(q.split())
    scored = []
    for p in load_pois():
        hay = _fold(p["name"].get("vi", "") + " " + p["name"].get("en", ""))
        score = 3 if q in hay else len(words & set(hay.split())) / max(1, len(words))
        if score >= 0.75:
            scored.append((score, p))
    scored.sort(key=lambda x: -x[0])
    keys = ["id", "name", "price_vnd", "open", "close", "closed_days", "visit_minutes", "indoor",
            "notes_vi", "notes_en", "description_vi", "description_en", "source"]
    found = [{k: p.get(k) for k in keys} for _, p in scored[:limit]]
    return {"found": found, "note": None if found else "Không có địa điểm này trong dữ liệu — nói rõ là không có."}


def _slim_poi(p: dict) -> dict:
    keys = ["id", "name", "category", "tags", "indoor", "price_vnd", "open", "close",
            "closed_days", "visit_minutes", "notes_vi", "notes_en"]
    return {k: p[k] for k in keys if k in p}


def dispatch(name: str, args: dict, state: dict):
    """Chạy tool, cập nhật state, trả kết quả gọn để đưa lại cho LLM."""
    date = args.get("date") or state.get("date")
    if name == "lookup_poi":
        return lookup_poi(args.get("name", ""))
    if name == "search_pois" and state.get("anchor"):
        # "gợi ý quanh Văn Miếu": model hay coi tên điểm là khu vực → bỏ, xếp theo khoảng cách tới điểm neo
        state["area"] = None
        return search_near(args, date, state)
    if name == "search_pois" and args.get("area"):
        return search_in_area(args, date, state)
    if name == "search_pois":
        state["area"] = None  # tìm không theo khu vực → bỏ khu vực cũ
        res = search_balanced(args.get("interests", []), args.get("group_type", "friends"),
                              int(args.get("max_price", 10**9)), bool(args.get("indoor_only", False)),
                              int(args.get("top_k", 15)), date)
        return [_slim_poi(p) for p in res]
    if name == "plan_route":
        fallback = default_start(state)
        start = (args.get("start_lat", fallback[0]), args.get("start_lng", fallback[1]))
        if state.get("named_start_turn") or state.get("destination_id"):
            # khách vừa nói "đang ở X" / đang hỏi đường tới một điểm: xuất phát do code đặt, bỏ toạ độ LLM tự đoán.
            # Hỏi đường thì đi từ chỗ khách đang đứng (nói rõ / GPS / Hồ Gươm), không từ tâm khu vực model tự chọn.
            start = fallback if state.get("named_start") or not state.get("destination_id") else                 default_start({**state, "area": None})
        state["plan_start"] = start
        # Ngân sách do code giữ (agent.llm.apply_budget_from_text) thắng số LLM tự đưa vào.
        # Lần lập lịch đầu chưa có thì lấy số LLM tách từ câu khách rồi giữ lại.
        if state.get("budget_vnd") is None:
            state["budget_vnd"] = int(args["budget_vnd"])
        budget = int(state["budget_vnd"])
        # Điểm khách đã bảo bỏ (agent.llm.apply_exclusion_from_text) không bao giờ quay lại lịch
        # model đôi khi đưa tên thay cho id ("Di tích Nhà tù Hỏa Lò") → đổi về id nếu khớp đúng tên
        from rag.search import get_poi, load_pois
        by_name = {_fold(n): p["id"] for p in load_pois() for n in p["name"].values()}
        ids = [i if get_poi(i) else by_name.get(_fold(str(i))) for i in args["poi_ids"]]
        args = {**args, "poi_ids": [i for i in ids if i]}  # id model tự bịa (vd "di-tich-nha-tu-hoa-lo") → bỏ
        excluded = set(state.get("excluded_ids") or [])
        if excluded:
            args = {**args, "poi_ids": [i for i in args["poi_ids"] if i not in excluded]}
        if state.get("anchor") and state.get("last_search_ids"):
            # gợi ý quanh một điểm: đưa ĐỦ ứng viên gần cho solver (model hay tự cắt bớt → ra ít điểm hơn khách xin)
            args = {**args, "poi_ids": list(dict.fromkeys(list(args["poi_ids"]) + [
                i for i in state["last_search_ids"] if i not in excluded]))}
        must = [m for m in (state.get("must_ids") or []) if m not in excluded]
        first = state.get("destination_id") if state.get("destination_id") not in excluded else None
        plan = plan_route(args["poi_ids"], start, args.get("start_time", DEFAULT_START_TIME),
                          args.get("end_time", DEFAULT_END_TIME), budget,
                          int(args["n_people"]), args.get("vehicle", "car"), date,
                          must_ids=must, first_id=first, max_stops=state.get("max_stops"))
        state["route_args"] = {**args, "budget_vnd": budget}
        state["plan"] = plan
        out = {k: v for k, v in plan.items() if k != "polyline"}  # polyline dài, LLM không cần
        out["summary"] = plan_summary(plan)  # số đã tính sẵn — LLM chép đúng các số này
        loc, named = state.get("location"), state.get("named_start")
        state["start_label"] = (named["name"] if named else
                                "vị trí hiện tại của bạn (GPS)" if loc and tuple(start) == (loc["lat"], loc["lng"]) else
                                "Hồ Gươm (điểm xuất phát mặc định)" if tuple(start) == tuple(DEFAULT_START) else
                                "điểm xuất phát đã chọn")
        facts = route_facts(plan, state)
        if facts:
            out["route_facts"] = facts  # chỉ đường tới điểm đến + khoảng cách gợi ý — tính bằng code
        return out
    if name == "get_weather":
        w = get_weather(date or args["date"], *DEFAULT_START)
        state["weather"] = w
        return w
    if name == "narrate":
        return narrate(args["poi_id"], args.get("lang", "vi"))
    return {"error": "tool không tồn tại: %s" % name}


def search_balanced(interests: list, group_type: str, max_price: int, indoor_only: bool, top_k: int,
                    date: str | None) -> list:
    """Nhiều sở thích (vd lịch sử + ẩm thực): lấy kết quả RIÊNG cho từng sở thích rồi xen kẽ, để sở thích nào cũng
    có mặt trong top_k. Xếp chung một danh sách thì điểm lịch sử (rất nhiều) chiếm hết chỗ, quán ăn bị cắt."""
    interests = [i for i in (interests or []) if i]
    if len(interests) <= 1:
        return search_pois(interests, group_type, max_price, indoor_only, top_k, date)
    lists = [search_pois([i], group_type, max_price, indoor_only, top_k, date) for i in interests]
    out, seen = [], set()
    for rank in range(max((len(x) for x in lists), default=0)):
        for lst in lists:
            if rank < len(lst) and lst[rank]["id"] not in seen:
                seen.add(lst[rank]["id"])
                out.append(lst[rank])
    return out[:top_k]


def dumps(obj) -> str:
    return json.dumps(obj, ensure_ascii=False)
