"""Tùng — kiểm lịch trình bằng code. Trả danh sách vi phạm; rỗng = lịch sạch.

Dùng ở 3 chỗ:
  - plan_route: kiểm kết quả OR-Tools (có vi phạm → quay về greedy) và kết quả greedy
  - eval: metric "0 vi phạm giờ mở cửa / ngân sách / chồng giờ", chấm bằng code (eval/metric_spec.yaml)
  - test tay: python -c "from routing.validate import validate_plan; ..."

Không dùng LLM, không gọi mạng. Thời gian di chuyển chỉ kiểm khi truyền `travel(a, b) -> phút`
(a = None nghĩa là điểm xuất phát, b = poi_id).
"""
from typing import Callable

from rag.search import get_poi, is_open_on, is_schedulable


def to_min(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def to_hhmm(minutes: int) -> str:
    return "%02d:%02d" % (minutes // 60, minutes % 60)


def validate_plan(plan: dict, start_time: str, end_time: str, budget_vnd: int, n_people: int,
                  date: str | None = None, travel: Callable[[str | None, str], int] | None = None) -> list[str]:
    v = []
    start, end = to_min(start_time), to_min(end_time)
    stops = plan.get("stops", [])
    seen, prev_id, prev_depart, total = set(), None, start, 0

    for k, s in enumerate(stops, 1):
        pid = s.get("poi_id")
        tag = "#%d %s" % (k, pid)
        p = get_poi(pid)
        if not p:
            v.append("%s: POI không tồn tại" % tag)
            continue
        if pid in seen:
            v.append("%s: đi lại điểm đã đi" % tag)
        seen.add(pid)
        if not is_schedulable(p):
            v.append("%s: thiếu giá / giờ mở cửa nhưng vẫn xếp" % tag)
            continue
        if not is_open_on(p, date):
            v.append("%s: đóng cửa ngày %s" % (tag, date))

        arrive, depart = to_min(s["arrive"]), to_min(s["depart"])
        if arrive < to_min(p["open"]):
            v.append("%s: đến %s trước giờ mở %s" % (tag, s["arrive"], p["open"]))
        if depart > to_min(p["close"]):
            v.append("%s: rời %s sau giờ đóng %s" % (tag, s["depart"], p["close"]))
        if depart - arrive < p["visit_minutes"]:
            v.append("%s: tham quan %d phút < %d phút cần" % (tag, depart - arrive, p["visit_minutes"]))
        if depart > end:
            v.append("%s: rời %s sau giờ kết thúc %s" % (tag, s["depart"], end_time))
        if arrive < prev_depart:
            v.append("%s: đến %s trước khi rời điểm trước (%s) — chồng giờ" % (tag, s["arrive"], to_hhmm(prev_depart)))
        elif travel is not None:
            need = travel(prev_id, pid)
            if arrive < prev_depart + need:
                v.append("%s: đến %s nhưng đi từ điểm trước mất %d phút (sớm nhất %s)"
                         % (tag, s["arrive"], need, to_hhmm(prev_depart + need)))

        expect_cost = p["price_vnd"] * n_people
        if s.get("cost") != expect_cost:
            v.append("%s: tiền %s ≠ giá vé × số người = %d" % (tag, s.get("cost"), expect_cost))
        total += expect_cost
        prev_id, prev_depart = pid, depart

    if plan.get("total_cost") != total:
        v.append("total_cost %s ≠ tổng tiền từng điểm %d" % (plan.get("total_cost"), total))
    if total > budget_vnd:
        v.append("tổng tiền %d vượt ngân sách %d" % (total, budget_vnd))
    for d in plan.get("dropped", []):
        if d in seen:
            v.append("%s vừa nằm trong lịch vừa nằm trong dropped" % d)
    return v
