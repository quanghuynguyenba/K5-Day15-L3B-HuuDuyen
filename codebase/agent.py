"""Một agent cho lát cắt: lịch một ngày ở Hà Nội.

Đường đi đổi theo câu (từ chối / hỏi lại / xếp lịch). Tối đa 4 bước có gọi model hoặc công cụ.
Giờ và tiền trong câu trả lời lấy từ plan_route. Model giả không được ghi đè các số đó.
"""
import re

from ai import call_model
from tools import get_weather, plan_route, search_pois
from tracing import note

SYSTEM = (
    "Bạn là trợ lý lập lịch nháp một ngày ở Hà Nội. "
    "Chỉ diễn đạt lại lịch do công cụ trả. Không bịa giờ, giá, điểm. "
    "Không đặt vé, không nhận thanh toán, số thẻ hay OTP. "
    "Thiếu số người, ngân sách hoặc khung giờ thì hỏi đúng một ý."
)
MAX_STEPS = 4

REFUSE = (
    "Mình không đặt vé, không thanh toán và không nhận số thẻ hay OTP. "
    "Mình chỉ lập lịch nháp. Bạn tự mua vé tại điểm hoặc kênh chính thức."
)


def _norm(text):
    return text.lower()


def _people(text):
    match = re.search(r"(\d+)\s*người", _norm(text))
    return int(match.group(1)) if match else None


def _budget(text):
    raw = _norm(text)
    trieu = re.search(r"(\d+)\s*triệu", raw)
    if trieu:
        return int(trieu.group(1)) * 1000000
    digits = re.search(r"(\d{5,})", raw)
    if digits:
        return int(digits.group(1))
    return None


def _window(text):
    match = re.search(r"từ\s*(\d{1,2})h\s*đến\s*(\d{1,2})h", _norm(text))
    if not match:
        return None
    return "%02d:00" % int(match.group(1)), "%02d:00" % int(match.group(2))


def _interests(text):
    raw = _norm(text)
    found = []
    if "lịch sử" in raw or "lich su" in raw:
        found.append("history")
    if "ẩm thực" in raw or "am thuc" in raw:
        found.append("food")
    if "bảo tàng" in raw or "bao tang" in raw:
        found.append("museum")
    return found


def _closed_day(text):
    raw = _norm(text)
    if "thứ hai" in raw or "thu hai" in raw:
        return "mon"
    return ""


def _excluded(text):
    raw = _norm(text)
    if "bỏ bảo tàng" in raw or "bo bao tang" in raw:
        return ["museum"]
    return []


def _missing_place(text):
    match = re.search(r"thêm\s+(.+?)\s+vào", text, flags=re.IGNORECASE)
    if not match:
        return ""
    name = match.group(1).strip(" .")
    known = ("văn miếu", "hoàng thành", "bảo tàng", "phở", "bún chả", "hồ gươm", "nhà thờ")
    if any(part in name.lower() for part in known):
        return ""
    return name


def _refuses(text):
    raw = _norm(text)
    keys = ("đặt vé", "dat ve", "thanh toán", "thanh toan", "số thẻ", "so the",
            "otp", "mật khẩu", "mat khau", "trừ ", "giữ chỗ", "giu cho")
    return any(key in raw for key in keys)


def _ask(text):
    if _people(text) is None:
        return "Đi mấy người?"
    if _budget(text) is None:
        return "Ngân sách cả ngày là bao nhiêu đồng?"
    if _window(text) is None:
        return "Đi từ mấy giờ đến mấy giờ?"
    raw = _norm(text)
    if not _interests(text) and ("sao cũng được" in raw or "so cung duoc" in raw):
        return "Bạn muốn ưu tiên sở thích nào: lịch sử, ẩm thực, hay bảo tàng?"
    if not _interests(text):
        return "Bạn muốn ưu tiên sở thích nào: lịch sử, ẩm thực, hay bảo tàng?"
    return ""


def _format_plan(plan, missing_name, rainy):
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


def answer(text: str) -> dict:
    note("agent: bắt đầu, tối đa %d bước" % MAX_STEPS)
    if _refuses(text):
        note("dừng: từ chối đặt vé hoặc dữ liệu thanh toán")
        call_model(SYSTEM, "Người dùng đòi đặt vé hoặc đưa dữ liệu thanh toán. Từ chối, không nhắc lại số.")
        return {"output": REFUSE}

    question = _ask(text)
    if question:
        note("dừng: thiếu thông tin, hỏi một câu")
        call_model(SYSTEM, "Hỏi đúng một ý còn thiếu: " + question)
        return {"output": question}

    window = _window(text)
    weather = get_weather("2026-11-28", "mưa" in _norm(text))
    found = search_pois(
        _interests(text),
        bool(weather["is_rainy"]),
        _excluded(text),
        _closed_day(text),
        _budget(text),
        _people(text),
    )
    plan = plan_route(
        [poi["id"] for poi in found],
        window[0],
        window[1],
        _budget(text),
        _people(text),
    )
    note("dừng: đã có lịch từ công cụ, 3 công cụ + 1 lần gọi model")
    rendered = _format_plan(plan, _missing_place(text), bool(weather["is_rainy"]))
    call_model(SYSTEM, "Diễn đạt lại, giữ nguyên mọi số:\n" + rendered)
    return {"output": rendered}
