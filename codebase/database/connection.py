"""PostgreSQL + pgvector connection helpers for codebase/."""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_DATABASE_URL = "postgresql://travel:travel@localhost:5432/travel"


def _load_env_if_needed():
    env_path = os.path.join(ROOT, ".env")
    if not os.path.exists(env_path):
        return
    with open(env_path, encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def get_database_url() -> str:
    _load_env_if_needed()
    return (os.environ.get("DATABASE_URL") or "").strip()


def get_connection(timeout_s: int = 3):
    """Open and return a psycopg connection with pgvector registered."""
    import psycopg
    from pgvector.psycopg import register_vector

    url = get_database_url() or DEFAULT_DATABASE_URL
    conn = psycopg.connect(url, connect_timeout=timeout_s)
    register_vector(conn)
    return conn


def is_db_available() -> bool:
    """Return True if DATABASE_URL is reachable and poi_chunks table exists."""
    url = get_database_url()
    if not url:
        return False
    try:
        with get_connection(timeout_s=2) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM poi_chunks LIMIT 1;")
        return True
    except Exception:
        return False
