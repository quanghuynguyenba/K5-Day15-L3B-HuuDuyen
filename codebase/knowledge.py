"""Runtime RAG retrieval over PostgreSQL + pgvector, with cross-language and JSON fallback."""
import json
import os
import sys
from typing import Any, Optional

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

POI_PATH = os.path.join(ROOT, "data", "pois.json")
EMPTY_MSG = "Không có trong dữ liệu điểm Hà Nội."


def _load_pois_json() -> list[dict[str, Any]]:
    with open(POI_PATH, encoding="utf-8") as f:
        return json.load(f)


def _fallback_keyword_search(query: str, top_k: int = 5, filters: Optional[dict[str, Any]] = None) -> list[dict[str, Any]]:
    """Keyword/tag search over data/pois.json when Postgres is unavailable."""
    q = (query or "").lower().strip()
    terms = [t for t in q.replace(",", " ").split() if len(t) >= 2]
    filters = filters or {}
    indoor_only = filters.get("indoor_only")
    category = filters.get("category")
    max_price = filters.get("max_price")
    lang = filters.get("lang", "vi")

    scored = []
    for poi in _load_pois_json():
        if indoor_only is True and not poi.get("indoor"):
            continue
        if category and poi.get("category") != category:
            continue
        if isinstance(max_price, int) and poi.get("price_vnd") is not None and poi["price_vnd"] > max_price:
            continue
        name = poi.get("name") or {}
        name_vi = name.get("vi") or ""
        name_en = name.get("en") or ""
        haystack = " ".join([
            name_vi,
            name_en,
            poi.get("category") or "",
            " ".join(poi.get("tags") or []),
            poi.get("description_vi") or "",
            poi.get("description_en") or "",
            poi.get("notes_vi") or "",
            poi.get("notes_en") or "",
        ]).lower()

        score = 0.0
        if q and q in haystack:
            score += 3.0
        for term in terms:
            if term in haystack:
                score += 1.0
        if score <= 0:
            continue

        desc = poi.get(f"description_{lang}") or poi.get("description_en") or poi.get("description_vi") or ""
        notes = poi.get(f"notes_{lang}") or poi.get("notes_en") or poi.get("notes_vi") or ""
        price = f"{poi['price_vnd']} VND" if poi.get("price_vnd") is not None else "chưa có dữ liệu"
        hours = f"{poi.get('open')}–{poi.get('close')}" if poi.get("open") and poi.get("close") else "chưa có dữ liệu"
        content = f"{name_vi} ({name_en}) | Giá vé: {price} | Giờ mở: {hours}\n{desc}\n{notes}".strip()
        scored.append((
            score,
            {
                "poi_id": poi["id"],
                "name": name_vi or name_en or poi["id"],
                "content": content,
                "source": poi.get("source") or "data/pois.json",
                "score": round(min(score / max(len(terms) + 3, 1), 1.0), 4),
                "price_vnd": poi.get("price_vnd"),
                "open": poi.get("open"),
                "close": poi.get("close"),
                "indoor": bool(poi.get("indoor")),
                "category": poi.get("category") or "",
                "backend": "json_fallback",
            },
        ))

    scored.sort(key=lambda item: -item[0])
    return [row for _, row in scored[:top_k]]


def retrieve(query: str, top_k: int = 5, filters: Optional[dict[str, Any]] = None) -> list[dict[str, Any]]:
    """Retrieve top-k POI chunks from PostgreSQL + pgvector (with cross-lang & JSON fallback)."""
    filters = filters or {}
    req_lang = (filters.get("lang") or "vi").lower()
    chunk_lang = req_lang if req_lang in ("vi", "en") else "en"
    try:
        from codebase.database.connection import get_connection, get_database_url
        from codebase.database.seed import embed_texts

        if not get_database_url():
            return _fallback_keyword_search(query, top_k=top_k, filters=filters)

        vectors, _mode = embed_texts([query])
        q_vec = vectors[0]

        where_clauses = ["c.lang = %s"]
        params: list[Any] = [q_vec, chunk_lang]

        if filters.get("indoor_only") is True:
            where_clauses.append("p.indoor = TRUE")
        if filters.get("category"):
            where_clauses.append("p.category = %s")
            params.append(filters["category"])
        if isinstance(filters.get("max_price"), int):
            where_clauses.append("(p.price_vnd IS NULL OR p.price_vnd <= %s)")
            params.append(filters["max_price"])

        params.extend([q_vec, top_k])
        where_sql = " AND ".join(where_clauses)
        sql = f"""
            SELECT c.poi_id, p.name_vi, c.content, p.source,
                   1 - (c.embedding <=> %s::vector) AS score,
                   p.price_vnd, p.open_time, p.close_time, p.indoor, p.category
            FROM poi_chunks c
            JOIN pois p ON p.id = c.poi_id
            WHERE {where_sql}
            ORDER BY c.embedding <=> %s::vector
            LIMIT %s;
        """
        with get_connection(timeout_s=2) as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                rows = cur.fetchall()

        return [
            {
                "poi_id": r[0],
                "name": r[1],
                "content": r[2],
                "source": r[3] or "postgres:poi_chunks",
                "score": round(float(r[4]), 4),
                "price_vnd": r[5],
                "open": r[6],
                "close": r[7],
                "indoor": bool(r[8]),
                "category": r[9] or "",
                "backend": "pgvector",
            }
            for r in rows
        ]
    except Exception:
        return _fallback_keyword_search(query, top_k=top_k, filters=filters)


def get_poi_context(poi_id: str, lang: str = "vi") -> str:
    """Read structured POI context from Postgres (lang -> en -> vi), falling back to data/pois.json."""
    try:
        from codebase.database.connection import get_connection, get_database_url

        if get_database_url():
            with get_connection(timeout_s=2) as conn:
                with conn.cursor() as cur:
                    for candidate in (lang, "en", "vi"):
                        cur.execute(
                            "SELECT content FROM poi_chunks WHERE poi_id = %s AND lang = %s LIMIT 1;",
                            (poi_id, candidate),
                        )
                        row = cur.fetchone()
                        if row:
                            return row[0]
    except Exception:
        pass

    for poi in _load_pois_json():
        if poi.get("id") == poi_id:
            desc = poi.get(f"description_{lang}") or poi.get("description_en") or poi.get("description_vi") or ""
            notes = poi.get(f"notes_{lang}") or poi.get("notes_en") or poi.get("notes_vi") or ""
            price = f"{poi['price_vnd']} VND" if poi.get("price_vnd") is not None else "chưa có dữ liệu"
            hours = f"{poi.get('open')}–{poi.get('close')}" if poi.get("open") and poi.get("close") else "chưa có dữ liệu"
            return f"{desc}\n{notes}\nGiá vé: {price} · Giờ mở: {hours}".strip()
    return ""


def get_poi_by_id(poi_id: str) -> Optional[dict[str, Any]]:
    """Read structured POI row from Postgres or data/pois.json."""
    try:
        from codebase.database.connection import get_connection, get_database_url

        if get_database_url():
            with get_connection(timeout_s=2) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """SELECT id, name_vi, name_en, lat, lng, category, tags, indoor,
                                  price_vnd, open_time, close_time, closed_days, visit_minutes,
                                  description_vi, description_en, notes_vi, notes_en, source
                           FROM pois WHERE id = %s LIMIT 1;""",
                        (poi_id,),
                    )
                    r = cur.fetchone()
                    if r:
                        return {
                            "id": r[0],
                            "name": {"vi": r[1], "en": r[2]},
                            "lat": r[3], "lng": r[4], "category": r[5], "tags": r[6],
                            "indoor": bool(r[7]), "price_vnd": r[8],
                            "open": r[9], "close": r[10], "closed_days": r[11],
                            "visit_minutes": r[12],
                            "description_vi": r[13], "description_en": r[14],
                            "notes_vi": r[15], "notes_en": r[16], "source": r[17],
                        }
    except Exception:
        pass
    for poi in _load_pois_json():
        if poi.get("id") == poi_id:
            return poi
    return None
