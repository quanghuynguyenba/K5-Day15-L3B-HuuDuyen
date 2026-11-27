"""Tùng — plan_route: chọn thứ tự đi + giờ đến/đi + chi phí.

Thứ tự: OR-Tools (routing/ortools_solver.py, ~2 giây) → kiểm bằng validate_plan → có vi phạm / lỗi / chưa cài
ortools thì dùng greedy nearest-neighbor (kiểm giờ mở cửa, ngày đóng cửa, ngân sách).
Mọi con số (giờ, tiền, phút) tính ở đây — LLM KHÔNG tự tính.

Kết quả (giữ hợp đồng cũ, thêm 2 khoá):
    stops, total_cost, total_minutes, polyline, dropped     — như trước
    dropped_reasons: {poi_id: not_found | missing_data | closed | budget | time | low_priority}
    solver: "ortools" | "greedy"
"""
import logging

from rag.search import get_poi, is_open_on, is_schedulable
from routing import ortools_solver
from routing.maps import directions, distance_matrix
from routing.validate import to_hhmm, to_min, validate_plan

log = logging.getLogger("optimizer")

USE_ORTOOLS = True


def _greedy(pois, matrix, start_min, end_min, budget_vnd, n_people):
    """Nearest-neighbor theo giờ đến sớm nhất. → [(poi, arrive, depart, cost)]"""
    remaining = list(enumerate(pois, 1))  # (chỉ số trong matrix, poi)
    now, cur, spent, out = start_min, 0, 0, []
    while remaining:
        best = None
        for node, p in remaining:
            arrive = max(now + matrix[cur][node], to_min(p["open"]))  # tới sớm thì chờ mở cửa
            depart = arrive + p["visit_minutes"]
            cost = p["price_vnd"] * n_people
            if depart > min(to_min(p["close"]), end_min) or spent + cost > budget_vnd:
                continue
            if best is None or arrive < best[2]:
                best = (node, p, arrive, depart, cost)
        if best is None:
            break
        node, p, arrive, depart, cost = best
        out.append((p, arrive, depart, cost))
        spent += cost
        now, cur = depart, node
        remaining.remove((node, p))
    return out


def _reason(p, matrix_row_from_start, node, start_min, end_min, budget_vnd, n_people):
    """Vì sao một POI hợp lệ không vào lịch — tính bằng code để LLM giải thích đúng."""
    if p["price_vnd"] * n_people > budget_vnd:
        return "budget"
    earliest = max(start_min + matrix_row_from_start[node], to_min(p["open"]))
    if earliest + p["visit_minutes"] > min(to_min(p["close"]), end_min):
        return "time"
    return "low_priority"


def plan_route(poi_ids: list[str], start_latlng: tuple, start_time: str,
               end_time: str, budget_vnd: int, n_people: int,
               vehicle: str = "car", date: str | None = None, solver: str = "auto") -> dict:
    """solver: "auto" (OR-Tools → greedy) | "greedy" (bỏ qua OR-Tools — để so sánh / debug)."""
    reasons = {}
    pois = []
    for pid in dict.fromkeys(poi_ids):  # bỏ id trùng, giữ thứ tự ưu tiên
        p = get_poi(pid)
        if not p:
            reasons[pid] = "not_found"
        elif not is_schedulable(p):
            reasons[pid] = "missing_data"
        elif not is_open_on(p, date):
            reasons[pid] = "closed"
        else:
            pois.append(p)

    # Ma trận MỘT lần: chỉ số 0 = điểm xuất phát, i + 1 = pois[i]
    points = [tuple(start_latlng)] + [(p["lat"], p["lng"]) for p in pois]
    matrix = distance_matrix(points, vehicle, skip_return_to_first=True)
    start_min, end_min = to_min(start_time), to_min(end_time)
    node_of = {p["id"]: i + 1 for i, p in enumerate(pois)}

    def travel(a, b):  # cho validate_plan: a = None là điểm xuất phát
        return matrix[node_of[a] if a else 0][node_of[b]]

    def build(order, solver):
        stops = [{"poi_id": p["id"], "arrive": to_hhmm(a), "depart": to_hhmm(d), "cost": c} for p, a, d, c in order]
        return {"stops": stops, "total_cost": sum(c for *_, c in order),
                "total_minutes": (order[-1][2] - start_min) if order else 0, "solver": solver}

    plan = None
    if USE_ORTOOLS and solver != "greedy":
        try:
            order = ortools_solver.solve(pois, matrix, start_min, end_min, budget_vnd, n_people)
            if order is not None:
                plan = build(order, "ortools")
                bad = validate_plan(plan, start_time, end_time, budget_vnd, n_people, date, travel)
                if bad:
                    log.warning("OR-Tools ra lịch vi phạm %s — dùng greedy", bad)
                    plan = None
        except Exception as e:
            log.warning("OR-Tools lỗi, dùng greedy: %s", e)
            plan = None
    if plan is None:
        plan = build(_greedy(pois, matrix, start_min, end_min, budget_vnd, n_people), "greedy")

    in_plan = {s["poi_id"] for s in plan["stops"]}
    for p in pois:
        if p["id"] not in in_plan:
            reasons[p["id"]] = _reason(p, matrix[0], node_of[p["id"]], start_min, end_min, budget_vnd, n_people)

    path = [points[0]] + [points[node_of[s["poi_id"]]] for s in plan["stops"]]
    plan["polyline"] = directions(path, vehicle)
    plan["dropped"] = list(reasons)
    plan["dropped_reasons"] = reasons
    return plan
