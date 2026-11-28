"""Tùng — xếp lịch bằng Google OR-Tools (VRP 1 xe, time windows, ngân sách, được bỏ điểm).

Mô hình:
  - Nút 0 = điểm xuất phát · 1..n = POI · n+1 = điểm kết thúc giả (đi tới tốn 0 phút → lịch không quay về).
  - Chiều "Time": chuyển i → j = di chuyển(i, j) + tham quan(i); slack = chờ mở cửa.
    Giờ đến POI ∈ [open, min(close, end_time) − visit_minutes] → tham quan xong trước khi đóng cửa / hết ngày.
  - Chiều "Cost": cộng giá vé × số người của từng điểm, tối đa = ngân sách.
  - Disjunction: được bỏ POI, mỗi điểm bỏ bị phạt. Phạt cơ bản > cả ngày di chuyển → ưu tiên đi được NHIỀU điểm nhất.
    Cộng thêm PRIORITY_STEP phút cho mỗi bậc hạng (hạng = thứ tự trong poi_ids, search_pois đã xếp theo mức hợp
    sở thích): điểm hạng cao hơn 1 bậc "đáng" đi vòng thêm tối đa PRIORITY_STEP phút.
  - Mục tiêu: ít phút di chuyển nhất.

solve(...) trả danh sách (poi, arrive_min, depart_min, cost) theo thứ tự đi, hoặc None nếu không chạy được
(chưa cài ortools, không có lời giải) — khi đó optimizer quay về greedy.
"""
import logging

log = logging.getLogger("ortools")

TIME_LIMIT_S = 2
PRIORITY_STEP = 10  # phút di chuyển đổi lấy 1 bậc hạng ưu tiên


def solve(pois: list[dict], matrix: list[list[int]], start_min: int, end_min: int,
          budget_vnd: int, n_people: int, time_limit_s: int = TIME_LIMIT_S,
          must: set | None = None, first: str | None = None, max_stops: int | None = None):
    """pois: POI đã lọc, theo thứ tự ưu tiên. matrix: phút di chuyển, chỉ số 0 = điểm xuất phát, i+1 = pois[i].
    must: id khách chỉ đích danh (vd "muốn đến Văn Miếu") — phạt bỏ cực lớn, gần như bắt buộc.
    first: id phải là điểm dừng đầu tiên (điểm đến khách hỏi đường). max_stops: số điểm tối đa ("gợi ý 5 điểm")."""
    must = set(must or ())
    try:
        from ortools.constraint_solver import pywrapcp, routing_enums_pb2
    except ImportError:
        log.warning("Chưa cài ortools — dùng greedy")
        return None
    if not pois:
        return []

    def to_min(hhmm):
        h, m = hhmm.split(":")
        return int(h) * 60 + int(m)

    n = len(pois)
    end_node = n + 1
    visit = [0] + [p["visit_minutes"] for p in pois] + [0]
    price = [0] + [p["price_vnd"] * n_people for p in pois] + [0]

    def travel(i, j):
        if j == end_node or i == j:
            return 0
        if i == end_node:
            return 0
        return matrix[i][j]

    manager = pywrapcp.RoutingIndexManager(n + 2, 1, [0], [end_node])
    routing = pywrapcp.RoutingModel(manager)

    def arc_cost(fi, ti):
        return travel(manager.IndexToNode(fi), manager.IndexToNode(ti))

    def arc_time(fi, ti):
        i, j = manager.IndexToNode(fi), manager.IndexToNode(ti)
        return travel(i, j) + visit[i]

    cost_cb = routing.RegisterTransitCallback(arc_cost)
    time_cb = routing.RegisterTransitCallback(arc_time)
    money_cb = routing.RegisterUnaryTransitCallback(lambda fi: price[manager.IndexToNode(fi)])
    routing.SetArcCostEvaluatorOfAllVehicles(cost_cb)

    day = max(1, end_min - start_min)
    routing.AddDimension(time_cb, day, 24 * 60, False, "Time")
    time = routing.GetDimensionOrDie("Time")
    routing.AddDimension(money_cb, 0, max(0, budget_vnd), True, "Cost")

    time.CumulVar(routing.Start(0)).SetRange(start_min, start_min)
    time.CumulVar(routing.End(0)).SetRange(start_min, end_min)

    base = day + 1
    for k, p in enumerate(pois):
        node = k + 1
        index = manager.NodeToIndex(node)
        lo = max(to_min(p["open"]), start_min)
        hi = min(to_min(p["close"]), end_min) - p["visit_minutes"]
        penalty = base * (n + 1) + PRIORITY_STEP * (n - k)  # bỏ 2 điểm luôn tệ hơn bỏ 1 điểm bất kỳ
        if p["id"] in must:
            penalty *= 100 * (n + 1)  # bỏ điểm khách chỉ đích danh tệ hơn bỏ mọi điểm khác cộng lại
        if lo > hi or price[node] > budget_vnd:
            # không thể xếp dù đi một mình → buộc bỏ (vẫn khai disjunction để mô hình khả thi)
            routing.AddDisjunction([index], 0)
            routing.solver().Add(routing.ActiveVar(index) == 0)
            continue
        time.CumulVar(index).SetRange(lo, hi)
        routing.AddDisjunction([index], penalty)
        if first and p["id"] == first:
            routing.solver().Add(routing.NextVar(routing.Start(0)) == index)  # đi thẳng tới điểm đến trước

    if max_stops:
        count_cb = routing.RegisterUnaryTransitCallback(lambda fi: 1 if 1 <= manager.IndexToNode(fi) <= n else 0)
        routing.AddDimension(count_cb, 0, int(max_stops), True, "Count")

    params = pywrapcp.DefaultRoutingSearchParameters()
    params.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    params.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    params.time_limit.FromMilliseconds(int(time_limit_s * 1000))

    solution = routing.SolveWithParameters(params)
    if solution is None:
        log.warning("OR-Tools không tìm được lời giải — dùng greedy")
        return None

    out = []
    index = routing.Start(0)
    while not routing.IsEnd(index):
        node = manager.IndexToNode(index)
        if 1 <= node <= n:
            p = pois[node - 1]
            arrive = solution.Min(time.CumulVar(index))
            out.append((p, arrive, arrive + p["visit_minutes"], price[node]))
        index = solution.Value(routing.NextVar(index))
    return out
