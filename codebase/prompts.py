"""System prompts, multilingual detection, structured intent/entity extraction, and task templates."""
import json
import os
import re
from typing import Any

SUPPORTED_LANGS = tuple(
    lang.strip().lower()
    for lang in (os.environ.get("SUPPORTED_LANGS") or "vi,en,ko,ja,zh").split(",")
    if lang.strip()
) or ("vi", "en", "ko", "ja", "zh")

LANG_NAMES = {
    "vi": "tiếng Việt",
    "en": "English",
    "ko": "한국어 (Korean)",
    "ja": "日本語 (Japanese)",
    "zh": "中文 (Chinese)",
}


def detect_lang(text: str) -> str:
    """Detect user language among vi, en, ko, ja, zh using script heuristics."""
    if not text:
        return "vi"
    if re.search(r"[가-힣]", text):
        return "ko"
    if re.search(r"[぀-ヿ]", text):
        return "ja"
    if re.search(r"[一-鿿]", text):
        return "zh"
    if re.search(r"[ăâđêôơưạảấầẩẫậắằẳẵặẹẻẽếềểễệỉịọỏốồổỗộớờởỡợụủứừửữựỳỵỷỹ]", text.lower()):
        return "vi"
    if re.search(r"\b(hanoi|temple|museum|budget|people|hours?|weather|recommend|itinerary|food|price|open)\b", text.lower()):
        return "en"
    return "vi"


def build_system_prompt(lang: str = "vi", memory_ctx: dict[str, Any] | None = None) -> str:
    lang_code = lang if lang in SUPPORTED_LANGS else "vi"
    lang_label = LANG_NAMES.get(lang_code, "tiếng Việt")
    base = (
        SYSTEM_PROMPT
        + f" Trả lời bằng ngôn ngữ của khách ({lang_label}, mã '{lang_code}'). "
        + "Khi trả lời bằng ngôn ngữ khác tiếng Việt, giữ tên địa điểm tiếng Việt trong ngoặc đơn nếu có."
    )
    if memory_ctx:
        st = memory_ctx.get("state") or {}
        if st.get("constraints") or st.get("current_plan") or st.get("summary"):
            compact = {
                "constraints": st.get("constraints") or {},
                "has_current_plan": bool(st.get("current_plan")),
                "summary": st.get("summary") or "",
            }
            base += "\nNgữ cảnh phiên hiện tại: " + json.dumps(compact, ensure_ascii=False)
    return base

SYSTEM_PROMPT = (
    "Bạn là trợ lý lập lịch nháp một ngày ở Hà Nội. "
    "Chỉ diễn đạt lại lịch và thông tin dựa trên dữ liệu công cụ hoặc tài liệu truy xuất. "
    "Không bịa giờ mở cửa, giá vé, địa điểm hay phần trăm thời tiết. "
    "Không đặt vé, không chốt phòng, không đặt tour, không nhận thanh toán, số thẻ hay OTP. "
    "Không lập lịch nhiều ngày hoặc thành phố khác ngoài Hà Nội. "
    "Nếu thiếu số người, ngân sách, khung giờ hoặc sở thích thì hỏi lại đúng một câu."
)

INTENT_SYSTEM_PROMPT = (
    "Bạn là bộ phân loại ý định (intent) và trích xuất thực thể (entity) cho trợ lý du lịch Hà Nội 1 ngày. "
    "Chỉ trả về DUY NHẤT một đối tượng JSON hợp lệ, không kèm giải thích."
)

INTENT_EXTRACTION_TEMPLATE = """Phân loại câu sau thành một trong các intent:
- PLAN_TRIP: lập lịch 1 ngày ở Hà Nội
- MODIFY_TRIP: sửa lịch hiện tại (đổi ngân sách, bỏ bảo tàng, thêm điểm, trời mưa)
- SEARCH_PLACE: tìm kiếm địa điểm ở Hà Nội
- RECOMMEND_PLACE: xin gợi ý địa điểm / quán ăn ở Hà Nội
- TRAVEL_INFO: hỏi thông tin du lịch (giờ mở cửa, giá vé, lưu ý, thời tiết) ở Hà Nội
- ESTIMATE_BUDGET: ước tính chi phí đi Hà Nội 1 ngày
- OUT_OF_SCOPE: yêu cầu nhiều ngày, thành phố/quốc gia khác ngoài Hà Nội
- REFUSE: yêu cầu đặt vé, giữ chỗ, chốt phòng, đặt tour, thanh toán, gửi số thẻ/OTP/mật khẩu

Trả về JSON đúng cấu trúc:
{{
  "intent": "...",
  "entities": {{
    "destination": "Hanoi",
    "start_date": "2026-11-28",
    "window": ["HH:MM", "HH:MM"] hoặc null,
    "budget_vnd": số nguyên hoặc null,
    "interests": ["history" | "food" | "museum" | "culture" | "nature" | "architecture" | "photo"],
    "n_people": số nguyên hoặc null,
    "transportation": chuỗi hoặc null,
    "language": "vi" | "en" | "ko" | "ja" | "zh",
    "exclusions": ["museum", ...],
    "rainy": true | false | null,
    "closed_day": "" | "mon" | "tue" | "wed" | "thu" | "fri" | "sat" | "sun",
    "requested_place": "tên điểm khách xin thêm nếu có, ngược lại chuỗi rỗng",
    "query": "từ khoá tìm kiếm ngắn"
  }},
  "missing_field": "n_people" | "budget_vnd" | "window" | "interests" | null
}}

Câu người dùng: {user_text}"""


def build_intent_prompt(user_text: str) -> str:
    return INTENT_EXTRACTION_TEMPLATE.format(user_text=user_text)


def build_trip_prompt(rendered_plan: str, entities_dict: dict[str, Any]) -> str:
    return (
        "Diễn đạt lại lịch nháp dưới đây cho tự nhiên, thân thiện, "
        "NHƯNG BẮT BUỘC giữ nguyên toàn bộ tên điểm, giờ đến/đi, giá tiền, Tổng tiền, Tổng phút và dòng Bỏ:\n"
        f"Ràng buộc đã trích xuất: {json.dumps(entities_dict, ensure_ascii=False)}\n\n"
        f"{rendered_plan}"
    )


def build_rag_prompt(intent: str, query: str, chunks: list[dict[str, Any]], entities_dict: dict[str, Any]) -> str:
    if not chunks:
        return (
            f"Intent: {intent}\nCâu hỏi: {query}\n"
            "Kết quả truy xuất: RỖNG (không có trong dữ liệu).\n"
            "Hãy trả lời ngắn gọn rằng thông tin này không có trong dữ liệu điểm Hà Nội, tuyệt đối không bịa giờ hay giá."
        )
    context_lines = []
    for i, c in enumerate(chunks, start=1):
        src = c.get("source") or "data/pois.json"
        score = c.get("score")
        score_txt = f" (score={score:.3f})" if isinstance(score, (int, float)) else ""
        context_lines.append(f"[{i}]{score_txt} {c.get('content', '')}\nNguồn: {src}")
    context = "\n\n".join(context_lines)
    return (
        f"Intent: {intent}\n"
        f"Ràng buộc: {json.dumps(entities_dict, ensure_ascii=False)}\n"
        f"Câu hỏi: {query}\n\n"
        f"Tài liệu truy xuất từ cơ sở dữ liệu:\n{context}\n\n"
        "Chỉ trả lời dựa trên tài liệu trên. Giữ nguyên tên điểm, giờ mở cửa, giá vé và nguồn nếu có. Không bịa thêm."
    )


def build_budget_prompt(query: str, budget_summary: str) -> str:
    return (
        "Dựa vào số liệu tính từ công cụ dưới đây, hãy giải thích ngắn gọn chi phí dự kiến cho khách, "
        "giữ nguyên mọi con số:\n"
        f"Câu hỏi: {query}\n\n{budget_summary}"
    )
