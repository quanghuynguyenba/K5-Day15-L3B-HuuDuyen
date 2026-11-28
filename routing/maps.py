"""Tùng — thời gian di chuyển + đường đi qua TomTom, có cache và fallback.

Nguồn, theo thứ tự: cache → TomTom API → Haversine × 1.4 / tốc độ nội thành (đường: nối thẳng).
Lỗi mạng, hết quota, sai key: KHÔNG làm sập app; lỗi một lần → ngừng gọi TomTom COOLDOWN_S giây.

Cache: data/cache/maps_cache.json (commit được — tính sẵn trước demo bằng `python -m routing.warm_cache`).
    "matrix": {"lat,lng|lat,lng|vehicle": phút}
    "legs":   {"lat,lng|lat,lng|vehicle": [[lat, lng], ...]}

TomTom (https://api.tomtom.com, key ở TOMTOM_API_KEY):
    POST /routing/matrix/2?key=...   body {"origins":[{"point":{"latitude","longitude"}}], "destinations":[...],
                                           "options":{"travelMode":..., "routeType":"fastest"}}
        → data[k] = {"originIndex", "destinationIndex", "routeSummary":{"travelTimeInSeconds"}} hoặc "detailedError"
    GET  /routing/1/calculateRoute/lat,lng:lat,lng:.../json?key=...&travelMode=...
        → routes[0].legs[i].points = [{"latitude","longitude"}, ...]   (một lần gọi cho cả tuyến)
"""
import json
import logging
import math
import os
import threading
import time
import urllib.parse
import urllib.request

from config import CACHE_DIR, TOMTOM_API_KEY, USE_TOMTOM

log = logging.getLogger("maps")

BASE_URL = "https://api.tomtom.com"
TIMEOUT_S = 10
# Số ô (origins × destinations) tối đa mỗi lần gọi matrix đồng bộ — đo thật 27/11/2026: 200 qua, 210 bị 400
MAX_CELLS = 200
MAX_ROUTE_POINTS = 150

SPEED_KMH = {"car": 20, "motorbike": 25, "walk": 4.5}
DETOUR = 1.4
# Tên phương tiện của app → travelMode của TomTom. None = không gọi API, dùng Haversine.
# Đo thật 27/11/2026: Matrix v2 từ chối "motorcycle" (400) → xe máy dùng thời gian ô tô trong ma trận.
# calculateRoute nhận "motorcycle" nhưng ở Hà Nội trả cùng thời gian + cùng tuyến với ô tô.
MATRIX_MODE = {"car": "car", "motorbike": "car", "walk": "pedestrian"}
ROUTE_MODE = {"car": "car", "motorbike": "motorcycle", "walk": "pedestrian"}

CACHE_PATH = os.path.join(CACHE_DIR, "maps_cache.json")
COOLDOWN_S = 60

_lock = threading.Lock()
_cache = None
_down_until = 0.0
stats = {"api_calls": 0, "fallback_pairs": 0}  # để debug / in ở warm_cache


# ---------------------------------------------------------------- tiện ích
def _haversine_km(a: tuple, b: tuple) -> float:
    lat1, lng1, lat2, lng2 = map(math.radians, (*a, *b))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lng2 - lng1) / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(h))


def haversine_minutes(a: tuple, b: tuple, vehicle: str = "car") -> int:
    km = _haversine_km(a, b) * DETOUR
    return max(1, round(km / SPEED_KMH.get(vehicle, 20) * 60))


def _fmt(p: tuple) -> str:
    return "%.5f,%.5f" % (p[0], p[1])


def _key(a: tuple, b: tuple, vehicle: str) -> str:
    return "%s|%s|%s" % (_fmt(a), _fmt(b), vehicle)


def _pt(p: tuple) -> dict:
    return {"point": {"latitude": p[0], "longitude": p[1]}}


def _ready() -> bool:
    return USE_TOMTOM and time.monotonic() >= _down_until


def _mark_down(e: Exception, what: str):
    global _down_until
    _down_until = time.monotonic() + COOLDOWN_S
    log.warning("TomTom %s lỗi, dùng Haversine / nối thẳng trong %ds: %s", what, COOLDOWN_S, e)


# ---------------------------------------------------------------- cache
def _load_cache() -> dict:
    global _cache
    if _cache is None:
        try:
            with open(CACHE_PATH, encoding="utf-8") as f:
                _cache = json.load(f)
        except (OSError, ValueError):
            _cache = {}
        _cache.setdefault("matrix", {})
        _cache.setdefault("legs", {})
    return _cache


def _save_cache():
    os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
    tmp = CACHE_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(_cache, f, ensure_ascii=False)
    os.replace(tmp, CACHE_PATH)


# ---------------------------------------------------------------- HTTP (tách riêng để test thay bằng phản hồi giả)
def _request(method: str, path: str, params: dict | None = None, body: dict | None = None) -> dict:
    params = {**(params or {}), "key": TOMTOM_API_KEY}
    url = "%s/%s?%s" % (BASE_URL, path, urllib.parse.urlencode(params))
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={"Content-Type": "application/json"})
    stats["api_calls"] += 1
    with urllib.request.urlopen(req, timeout=TIMEOUT_S) as r:
        return json.loads(r.read().decode("utf-8"))


# ---------------------------------------------------------------- matrix
def _fetch_matrix(points: list[tuple], pairs: set, vehicle: str, cache: dict) -> bool:
    """Gọi TomTom cho các cặp còn thiếu. Gom các điểm đi có cùng tập điểm đến vào chung một lần gọi
    (vd điểm xuất phát mới chỉ cần 1 × n, không phải (n+1) × (n+1)). Tập điểm đến tính cả chính điểm đi,
    để các hàng của một ma trận đầy đủ gộp được với nhau — tốn thêm ô đường chéo nhưng ít request hơn nhiều."""
    by_origin = {}
    for i, j in pairs:
        by_origin.setdefault(i, set()).add(j)
    groups = {}
    for i, dests in by_origin.items():
        groups.setdefault(frozenset(dests | {i}), []).append(i)

    changed = False
    for dests, origins in groups.items():
        dests = sorted(dests)
        for d0 in range(0, len(dests), MAX_CELLS):
            d_chunk = dests[d0:d0 + MAX_CELLS]
            per = max(1, MAX_CELLS // len(d_chunk))
            for o0 in range(0, len(origins), per):
                o_chunk = origins[o0:o0 + per]
                res = _request("POST", "routing/matrix/2", body={
                    "origins": [_pt(points[i]) for i in o_chunk],
                    "destinations": [_pt(points[j]) for j in d_chunk],
                    "options": {"travelMode": MATRIX_MODE[vehicle], "routeType": "fastest"},
                })
                for cell in res.get("data", []):
                    summ = cell.get("routeSummary")
                    oi, dj = o_chunk[cell["originIndex"]], d_chunk[cell["destinationIndex"]]
                    if not summ or oi == dj:
                        continue  # ô lỗi (detailedError) → để Haversine lo; ô đường chéo bỏ qua
                    cache[_key(points[oi], points[dj], vehicle)] = max(1, round(summ["travelTimeInSeconds"] / 60))
                    changed = True
    return changed


def distance_matrix(points: list[tuple], vehicle: str = "car", skip_return_to_first: bool = False) -> list[list[int]]:
    """Ma trận phút di chuyển giữa các điểm (lat, lng). Ô [i][j] = từ i đến j.
    skip_return_to_first=True: không xin các cặp (i → 0) — lịch trình không quay về điểm xuất phát,
    nên điểm xuất phát mới chỉ tốn 1 × n ô thay vì (n+1)²."""
    points = [tuple(p) for p in points]
    n = len(points)
    with _lock:
        cache = _load_cache()["matrix"]
        need = {(i, j) for i in range(n) for j in range(n)
                if i != j and not (skip_return_to_first and j == 0)
                and _key(points[i], points[j], vehicle) not in cache}
        if need and MATRIX_MODE.get(vehicle) and _ready():
            try:
                if _fetch_matrix(points, need, vehicle, cache):
                    _save_cache()
            except Exception as e:  # mạng, quota, key sai, JSON lạ…
                _mark_down(e, "matrix")
                if cache:
                    _save_cache()  # giữ phần đã lấy được trước khi lỗi

        out = [[0] * n for _ in range(n)]
        for i in range(n):
            for j in range(n):
                if i == j:
                    continue
                k = _key(points[i], points[j], vehicle)
                if k in cache:
                    out[i][j] = cache[k]
                else:
                    if (i, j) in need:
                        stats["fallback_pairs"] += 1
                    out[i][j] = haversine_minutes(points[i], points[j], vehicle)
        return out


def travel_minutes(a: tuple, b: tuple, vehicle: str = "car") -> int:
    """Một cặp điểm. Gọi nhiều lần thì dùng distance_matrix để gộp request."""
    return distance_matrix([a, b], vehicle)[0][1]


# ---------------------------------------------------------------- đường đi
def directions(points: list[tuple], vehicle: str = "car") -> list[list[float]]:
    """Polyline [[lat, lng], …] bám đường qua các điểm theo thứ tự.
    Còn thiếu chặng nào thì gọi TomTom MỘT lần cho cả tuyến, cache từng chặng. Chặng lỗi → nối thẳng."""
    points = [tuple(p) for p in points]
    if len(points) < 2:
        return [list(p) for p in points]
    with _lock:
        legs = _load_cache()["legs"]
        pairs = list(zip(points, points[1:]))
        missing = any(_key(a, b, vehicle) not in legs for a, b in pairs)
        if missing and ROUTE_MODE.get(vehicle) and len(points) <= MAX_ROUTE_POINTS and _ready():
            try:
                res = _request("GET", "routing/1/calculateRoute/%s/json" % ":".join(_fmt(p) for p in points),
                               params={"travelMode": ROUTE_MODE[vehicle], "routeType": "fastest"})
                for (a, b), leg in zip(pairs, res["routes"][0]["legs"]):
                    legs[_key(a, b, vehicle)] = [[q["latitude"], q["longitude"]] for q in leg["points"]]
                _save_cache()
            except Exception as e:
                _mark_down(e, "calculateRoute")
        path = [list(points[0])]
        for a, b in pairs:
            leg = legs.get(_key(a, b, vehicle)) or [list(a), list(b)]
            path.extend(leg[1:] if leg[0] == path[-1] else leg)
        return path


# ---------------------------------------------------------------- địa danh → toạ độ (cho "lịch ở Sơn Tây")
def geocode(query: str) -> dict | None:
    """Tên khu vực / địa danh ở Hà Nội → {"name", "lat", "lng", "radius_km"} qua TomTom Search (cache theo tên).
    radius_km lấy từ khung bao (viewport) của kết quả, kẹp trong [3, 20] km. Không có key / lỗi / không ra kết quả
    ở quanh Hà Nội → None (không đoán)."""
    import urllib.parse
    q = " ".join((query or "").split())
    if not q:
        return None
    key = q.casefold()
    with _lock:
        geo = _load_cache().setdefault("geocode", {})
        if key in geo:
            return geo[key] or None  # {} = đã tra, không có kết quả hợp lệ
    if not _ready():
        return None
    try:
        res = _request("GET", "search/2/geocode/%s.json" % urllib.parse.quote(q + ", Hà Nội"),
                       params={"countrySet": "VN", "limit": 1, "language": "vi-VN"})
    except Exception as e:
        _mark_down(e, "geocode")
        return None
    hit = (res.get("results") or [None])[0]
    # Chỉ nhận đơn vị hành chính (quận / huyện / thị xã / phường). Kết quả kiểu Street là TomTom "ép" tên gần giống
    # (vd "phố cổ" → "Phố Cồ Tấn", chữ vô nghĩa → một con phố bất kỳ); kết quả cả "Hà Nội" khi khách không hỏi
    # cả thành phố là do ", Hà Nội" nối thêm vào truy vấn — bỏ cả hai, để không lập lịch nhầm chỗ.
    whole_city = hit and (hit.get("address") or {}).get("freeformAddress", "").strip().casefold() in ("hà nội", "hanoi")
    asked_city = key.replace(" ", "") in ("hànội", "hanoi")
    if not hit or hit.get("type") != "Geography" or (whole_city and not asked_city):
        with _lock:
            _load_cache()["geocode"][key] = {}
            _save_cache()
        return None
    lat, lng = hit["position"]["lat"], hit["position"]["lon"]
    if _haversine_km((lat, lng), (21.0285, 105.8542)) > 80:  # ngoài vùng Hà Nội → bỏ
        return None
    vp = hit.get("viewport") or {}
    tl, br = vp.get("topLeftPoint"), vp.get("btmRightPoint")
    half_diag = _haversine_km((tl["lat"], tl["lon"]), (br["lat"], br["lon"])) / 2 if tl and br else 5
    out = {"name": (hit.get("address") or {}).get("freeformAddress") or q, "lat": lat, "lng": lng,
           "radius_km": round(min(20.0, max(3.0, half_diag * 1.5)), 1)}
    addr = hit.get("address") or {}
    level = {"Municipality": "municipality", "MunicipalitySubdivision": "subdivision"}.get(hit.get("entityType"))
    if level:  # khớp theo đúng tên đơn vị hành chính của từng POI (poi_admin) — chính xác hơn mọi hình bao
        out["level"] = level
        out["admin"] = addr.get("municipality") if level == "municipality" else addr.get("municipalitySubdivision")
    if tl and br:  # khung bao thật của đơn vị hành chính, nới ~0,5 km — dùng khi POI chưa có tên quận
        m = 0.0045
        out["bbox"] = [min(tl["lat"], br["lat"]) - m, min(tl["lon"], br["lon"]) - m,
                       max(tl["lat"], br["lat"]) + m, max(tl["lon"], br["lon"]) + m]
    with _lock:
        _load_cache()["geocode"][key] = out
        _save_cache()
    return out


def poi_admin(lat: float, lng: float) -> dict | None:
    """Toạ độ → {"municipality": quận / thị xã / huyện, "subdivision": phường / xã} qua TomTom reverse geocode.
    Cache theo toạ độ (POI đổi toạ độ thì tự tra lại). Lỗi / chưa có key → None."""
    key = "%.5f,%.5f" % (lat, lng)
    with _lock:
        adm = _load_cache().setdefault("admin", {})
        if key in adm:
            return adm[key]
    if not _ready():
        return None
    try:
        res = _request("GET", "search/2/reverseGeocode/%s.json" % key, params={"language": "vi-VN"})
    except Exception as e:
        _mark_down(e, "reverseGeocode")
        return None
    a = ((res.get("addresses") or [{}])[0]).get("address") or {}
    out = {"municipality": a.get("municipality"), "subdivision": a.get("municipalitySubdivision")}
    with _lock:
        _load_cache()["admin"][key] = out
        _save_cache()
    return out
