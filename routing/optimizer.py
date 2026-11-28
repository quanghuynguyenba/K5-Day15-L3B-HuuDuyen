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


def _greedy(pois, matrix, start_min, end_min, budget_vnd, n_people, must=(), first=None, max_stops=None):
    """Nearest-neighbor theo giờ đến sớm nhất. → [(poi, arrive, depart, cost)]
    first: đi điểm này trước nếu kịp. must: còn điểm bắt buộc kịp đi thì chọn trong số đó trước. max_stops: dừng."""
    remaining = list(enumerate(pois, 1))  # (chỉ số trong matrix, poi)
    now, cur, spent, out = start_min, 0, 0, []
    while remaining and (not max_stops or len(out) < max_stops):
        best = None
        pool = remaining
        if not out and first:
            pool = [x for x in remaining if x[1]["id"] == first] or remaining
        elif must:
            pool = [x for x in remaining if x[1]["id"] in must] or remaining
        for node, p in pool:
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


def _reason(p, matrix_row_from_start, node, start_min, end_min, budget_vnd, n_people, spent=0):
    """Vì sao một POI hợp lệ không vào lịch — tính bằng code để LLM giải thích đúng.
    spent = tổng tiền lịch đã chọn: thêm điểm này mà vượt ngân sách thì lý do là budget, không phải thời gian."""
    cost = p["price_vnd"] * n_people
    if cost > budget_vnd or (cost > 0 and spent + cost > budget_vnd):
        return "budget"
    earliest = max(start_min + matrix_row_from_start[node], to_min(p["open"]))
    if earliest + p["visit_minutes"] > min(to_min(p["close"]), end_min):
        return "time"
    return "low_priority"


def plan_route(poi_ids: list[str], start_latlng: tuple, start_time: str,
               end_time: str, budget_vnd: int, n_people: int,
               vehicle: str = "car", date: str | None = None, solver: str = "auto",
               must_ids: list | None = None, first_id: str | None = None, max_stops: int | None = None) -> dict:
    """solver: "auto" (OR-Tools → greedy) | "greedy" (bỏ qua OR-Tools — để so sánh / debug).
    must_ids: điểm khách chỉ đích danh (luôn được đưa vào danh sách, gần như bắt buộc).
    first_id: điểm phải đi đầu tiên (điểm đến khách hỏi đường). max_stops: số điểm tối đa."""
    must = [m for m in (must_ids or []) if m]
    if first_id and first_id not in must:
        must.insert(0, first_id)
    reasons = {}
    pois = []
    for pid in dict.fromkeys(must + list(poi_ids)):  # bỏ id trùng; điểm bắt buộc đứng đầu
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
            order = ortools_solver.solve(pois, matrix, start_min, end_min, budget_vnd, n_people,
                                         must=set(must), first=first_id, max_stops=max_stops)
            if order is not None:
                plan = build(order, "ortools")
                bad = validate_plan(plan, start_time, end_time, budget_vnd, n_people, date, travel)
                if first_id in node_of and plan["stops"] and plan["stops"][0]["poi_id"] != first_id:
                    bad.append("điểm đến %s không phải điểm đầu tiên" % first_id)
                if bad:
                    log.warning("OR-Tools ra lịch vi phạm %s — dùng greedy", bad)
                    plan = None
        except Exception as e:
            log.warning("OR-Tools lỗi, dùng greedy: %s", e)
            plan = None
    if plan is None:
        plan = build(_greedy(pois, matrix, start_min, end_min, budget_vnd, n_people,
                             must=set(must), first=first_id, max_stops=max_stops), "greedy")

    in_plan = {s["poi_id"] for s in plan["stops"]}
    full = bool(max_stops) and len(plan["stops"]) >= max_stops
    for p in pois:
        if full and p["id"] not in must:
            continue  # đủ số điểm khách xin — ứng viên dư không phải "bị bỏ", không báo lý do
        if p["id"] not in in_plan:
            reasons[p["id"]] = _reason(p, matrix[0], node_of[p["id"]], start_min, end_min, budget_vnd, n_people,
                                       plan["total_cost"])

    path = [points[0]] + [points[node_of[s["poi_id"]]] for s in plan["stops"]]
    plan["polyline"] = directions(path, vehicle)
    plan["dropped"] = list(reasons)
    plan["dropped_reasons"] = reasons
    return plan
