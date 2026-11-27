"""Tùng — plan_route: chọn thứ tự đi + giờ đến/đi + chi phí.

Bản hiện tại: greedy nearest-neighbor có kiểm giờ mở cửa, ngày đóng cửa và ngân sách (đúng mục "Fallback" trong TASK.md).
TODO (Tùng): OR-Tools có time windows + disjunction penalty, giới hạn ~2 giây; lỗi thì quay về greedy.
Mọi con số (giờ, tiền, phút) tính ở đây — LLM KHÔNG tự tính.
"""
from rag.search import get_poi, is_open_on, is_schedulable
from routing.goong import directions, travel_minutes


def _to_min(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def _to_hhmm(minutes: int) -> str:
    return "%02d:%02d" % (minutes // 60, minutes % 60)


def plan_route(poi_ids: list[str], start_latlng: tuple, start_time: str,
               end_time: str, budget_vnd: int, n_people: int,
               vehicle: str = "car", date: str | None = None) -> dict:
    pois = [p for p in (get_poi(i) for i in poi_ids) if p]
    dropped = [i for i in poi_ids if not get_poi(i)]
    dropped += [p["id"] for p in pois if not is_open_on(p, date) or not is_schedulable(p)]
    remaining = [p for p in pois if is_open_on(p, date) and is_schedulable(p)]

    now, end = _to_min(start_time), _to_min(end_time)
    pos = tuple(start_latlng)
    spent, stops, path = 0, [], [pos]

    while remaining:
        best = None
        for p in remaining:
            arrive = now + travel_minutes(pos, (p["lat"], p["lng"]), vehicle)
            arrive = max(arrive, _to_min(p["open"]))           # tới sớm thì chờ mở cửa
            depart = arrive + p["visit_minutes"]
            cost = p["price_vnd"] * n_people
            if depart > min(_to_min(p["close"]), end) or spent + cost > budget_vnd:
                continue
            if best is None or arrive < best[1]:
                best = (p, arrive, depart, cost)
        if best is None:
            break
        p, arrive, depart, cost = best
        stops.append({"poi_id": p["id"], "arrive": _to_hhmm(arrive), "depart": _to_hhmm(depart), "cost": cost})
        spent += cost
        now, pos = depart, (p["lat"], p["lng"])
        path.append(pos)
        remaining.remove(p)

    dropped += [p["id"] for p in remaining]
    return {
        "stops": stops,
        "total_cost": spent,
        "total_minutes": now - _to_min(start_time),
        "polyline": directions(path, vehicle),
        "dropped": dropped,
    }
