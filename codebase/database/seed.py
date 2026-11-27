"""Seed PostgreSQL + pgvector from data/pois.json.

Run from repo root:
    python -m codebase.database.seed
or:
    python codebase/database/seed.py
"""
import hashlib
import json
import math
import os
import sys
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from codebase.database.connection import _load_env_if_needed, get_connection  # noqa: E402

POI_PATH = os.path.join(ROOT, "data", "pois.json")
EMBED_DIM = 1536


def _local_hash_embedding(text: str, dim: int = EMBED_DIM) -> list[float]:
    """Deterministic normalized n-gram projection fallback when no embedding API key is configured."""
    vec = [0.0] * dim
    norm_text = " ".join(text.lower().split())
    tokens = norm_text.split()
    grams = list(tokens)
    for tok in tokens:
        if len(tok) >= 3:
            grams.extend(tok[i:i + 3] for i in range(len(tok) - 2))
    if not grams:
        grams = [norm_text or "empty"]
    for g in grams:
        digest = hashlib.blake2b(g.encode("utf-8"), digest_size=8).digest()
        idx = int.from_bytes(digest[:4], "big") % dim
        sign = 1.0 if (digest[4] & 1) == 0 else -1.0
        vec[idx] += sign
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def embed_texts(texts: list[str]) -> tuple[list[list[float]], str]:
    """Embed texts using OpenAI-compatible embeddings API, or deterministic local hash fallback."""
    _load_env_if_needed()
    api_key = (
        os.environ.get("EMBED_API_KEY")
        or os.environ.get("API_KEY")
        or os.environ.get("AI_API_KEY")
        or os.environ.get("LLM_API_KEY")
        or ""
    ).strip()
    embed_model = (os.environ.get("EMBED_MODEL") or "text-embedding-3-small").strip()
    base_url = (os.environ.get("EMBED_BASE_URL") or os.environ.get("LLM_BASE_URL") or "https://api.openai.com/v1").strip().rstrip("/")
    provider = (os.environ.get("MODEL_PROVIDER") or "fake").strip().lower()

    if not api_key or provider == "fake":
        return ([_local_hash_embedding(t) for t in texts], "local_hash")

    url = base_url if base_url.endswith("/embeddings") else f"{base_url}/embeddings"
    req = urllib.request.Request(
        url,
        data=json.dumps({"model": embed_model, "input": texts}).encode("utf-8"),
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        items = sorted(data["data"], key=lambda x: x["index"])
        return ([item["embedding"] for item in items], embed_model)
    except (urllib.error.HTTPError, urllib.error.URLError, KeyError, TimeoutError) as e:
        print(f"[seed] Embedding API unavailable ({e}); falling back to local_hash.", file=sys.stderr)
        return ([_local_hash_embedding(t) for t in texts], "local_hash")


def _build_chunk(poi: dict, lang: str) -> str:
    name = poi.get("name") or {}
    name_vi = name.get("vi") or poi["id"]
    name_en = name.get("en") or name_vi
    desc = poi.get(f"description_{lang}") or poi.get("description_vi") or ""
    notes = poi.get(f"notes_{lang}") or poi.get("notes_vi") or ""
    price = f"{poi['price_vnd']} VND" if poi.get("price_vnd") is not None else "chưa có dữ liệu"
    hours = f"{poi.get('open')}–{poi.get('close')}" if poi.get("open") and poi.get("close") else "chưa có dữ liệu"
    indoor_str = "trong nhà" if poi.get("indoor") else "ngoài trời"
    tags = ", ".join(poi.get("tags") or [])
    return (
        f"{name_vi} ({name_en}) | Loại: {poi.get('category', '')} | Tags: {tags} | "
        f"{indoor_str} | Giá vé: {price} | Giờ mở: {hours}\n"
        f"{desc}\n{notes}\nNguồn: {poi.get('source', '')}"
    ).strip()


def seed():
    with open(POI_PATH, encoding="utf-8") as f:
        pois = json.load(f)

    chunk_rows = []
    for poi in pois:
        for lang in ("vi", "en"):
            chunk_rows.append((poi, lang, _build_chunk(poi, lang)))

    texts = [row[2] for row in chunk_rows]
    vectors, mode = embed_texts(texts)

    with get_connection(timeout_s=5) as conn:
        with conn.cursor() as cur:
            for poi in pois:
                name = poi.get("name") or {}
                cur.execute(
                    """
                    INSERT INTO pois (
                        id, name_vi, name_en, lat, lng, category, tags, indoor,
                        price_vnd, open_time, close_time, closed_days, visit_minutes,
                        suitable_for, description_vi, description_en, notes_vi, notes_en, source
                    ) VALUES (
                        %(id)s, %(name_vi)s, %(name_en)s, %(lat)s, %(lng)s, %(category)s, %(tags)s, %(indoor)s,
                        %(price_vnd)s, %(open_time)s, %(close_time)s, %(closed_days)s, %(visit_minutes)s,
                        %(suitable_for)s, %(description_vi)s, %(description_en)s, %(notes_vi)s, %(notes_en)s, %(source)s
                    )
                    ON CONFLICT (id) DO UPDATE SET
                        name_vi = EXCLUDED.name_vi,
                        name_en = EXCLUDED.name_en,
                        lat = EXCLUDED.lat,
                        lng = EXCLUDED.lng,
                        category = EXCLUDED.category,
                        tags = EXCLUDED.tags,
                        indoor = EXCLUDED.indoor,
                        price_vnd = EXCLUDED.price_vnd,
                        open_time = EXCLUDED.open_time,
                        close_time = EXCLUDED.close_time,
                        closed_days = EXCLUDED.closed_days,
                        visit_minutes = EXCLUDED.visit_minutes,
                        suitable_for = EXCLUDED.suitable_for,
                        description_vi = EXCLUDED.description_vi,
                        description_en = EXCLUDED.description_en,
                        notes_vi = EXCLUDED.notes_vi,
                        notes_en = EXCLUDED.notes_en,
                        source = EXCLUDED.source,
                        updated_at = NOW();
                    """,
                    {
                        "id": poi["id"],
                        "name_vi": name.get("vi") or poi["id"],
                        "name_en": name.get("en") or name.get("vi") or poi["id"],
                        "lat": poi.get("lat"),
                        "lng": poi.get("lng"),
                        "category": poi.get("category") or "",
                        "tags": poi.get("tags") or [],
                        "indoor": bool(poi.get("indoor")),
                        "price_vnd": poi.get("price_vnd"),
                        "open_time": poi.get("open"),
                        "close_time": poi.get("close"),
                        "closed_days": poi.get("closed_days") or [],
                        "visit_minutes": poi.get("visit_minutes"),
                        "suitable_for": poi.get("suitable_for") or [],
                        "description_vi": poi.get("description_vi") or "",
                        "description_en": poi.get("description_en") or "",
                        "notes_vi": poi.get("notes_vi") or "",
                        "notes_en": poi.get("notes_en") or "",
                        "source": poi.get("source") or "",
                    },
                )

            for (poi, lang, content), vec in zip(chunk_rows, vectors):
                meta = {
                    "category": poi.get("category"),
                    "indoor": bool(poi.get("indoor")),
                    "price_vnd": poi.get("price_vnd"),
                    "source": poi.get("source") or "",
                    "embedding_mode": mode,
                }
                cur.execute(
                    """
                    INSERT INTO poi_chunks (poi_id, lang, content, metadata, embedding)
                    VALUES (%s, %s, %s, %s::jsonb, %s)
                    ON CONFLICT (poi_id, lang) DO UPDATE SET
                        content = EXCLUDED.content,
                        metadata = EXCLUDED.metadata,
                        embedding = EXCLUDED.embedding;
                    """,
                    (poi["id"], lang, content, json.dumps(meta, ensure_ascii=False), vec),
                )
        conn.commit()
    print(f"Seeded {len(pois)} POIs and {len(chunk_rows)} chunks (embedding={mode}).")


if __name__ == "__main__":
    seed()
