"""Phase 6: Session memory & user preferences in PostgreSQL, with in-memory fallback."""
import json
import os
import sys
from typing import Any, Optional

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

MAX_MESSAGES = 10
MAX_HISTORY_CHARS = 2400

_LOCAL_SESSIONS: dict[str, dict[str, Any]] = {}
_LOCAL_PREFS: dict[str, dict[str, Any]] = {}


def _default_state() -> dict[str, Any]:
    return {"constraints": {}, "current_plan": None, "pending_question": None, "summary": ""}


def _default_prefs() -> dict[str, Any]:
    return {"language": "vi", "interests": [], "budget_band": "", "travel_style": "", "transportation": ""}


def _db_conn():
    from codebase.database.connection import get_connection, get_database_url
    if not get_database_url():
        return None
    return get_connection(timeout_s=2)


def ensure_session(session_id: str, user_key: str = "default") -> None:
    try:
        conn = _db_conn()
        if conn is not None:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO sessions (session_id, user_key) VALUES (%s, %s) ON CONFLICT (session_id) DO UPDATE SET updated_at = NOW();",
                        (session_id, user_key),
                    )
                    cur.execute(
                        "INSERT INTO session_state (session_id) VALUES (%s) ON CONFLICT (session_id) DO NOTHING;",
                        (session_id,),
                    )
            conn.close()
            return
    except Exception:
        pass
    _LOCAL_SESSIONS.setdefault(session_id, {"user_key": user_key, "messages": [], "state": _default_state()})


def append_message(session_id: str, role: str, content: str) -> None:
    ensure_session(session_id)
    try:
        conn = _db_conn()
        if conn is not None:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO messages (session_id, role, content) VALUES (%s, %s, %s);",
                        (session_id, role, content),
                    )
            conn.close()
            _maybe_summarize_db(session_id)
            return
    except Exception:
        pass
    bucket = _LOCAL_SESSIONS[session_id]["messages"]
    bucket.append({"role": role, "content": content})
    if len(bucket) > MAX_MESSAGES or sum(len(m["content"]) for m in bucket) > MAX_HISTORY_CHARS:
        old = bucket[:-4]
        _LOCAL_SESSIONS[session_id]["state"]["summary"] = _compact_summary(
            _LOCAL_SESSIONS[session_id]["state"].get("summary", ""), old
        )
        _LOCAL_SESSIONS[session_id]["messages"] = bucket[-4:]


def _compact_summary(prev_summary: str, dropped_msgs: list[dict[str, str]]) -> str:
    bits = [f"{m['role']}: {m['content'][:120]}" for m in dropped_msgs]
    joined = (prev_summary + "\n" + "\n".join(bits)).strip()
    return joined[-800:]


def _maybe_summarize_db(session_id: str) -> None:
    try:
        conn = _db_conn()
        if conn is None:
            return
        with conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id, role, content FROM messages WHERE session_id = %s ORDER BY id ASC;", (session_id,))
                rows = cur.fetchall()
                if len(rows) > MAX_MESSAGES or sum(len(r[2]) for r in rows) > MAX_HISTORY_CHARS:
                    drop = rows[:-4]
                    cur.execute("SELECT summary FROM session_state WHERE session_id = %s;", (session_id,))
                    prev = (cur.fetchone() or [""])[0] or ""
                    new_sum = _compact_summary(prev, [{"role": r[1], "content": r[2]} for r in drop])
                    cur.execute("UPDATE session_state SET summary = %s, updated_at = NOW() WHERE session_id = %s;", (new_sum, session_id))
                    cur.execute("DELETE FROM messages WHERE id = ANY(%s);", ([r[0] for r in drop],))
        conn.close()
    except Exception:
        pass


def get_session_context(session_id: str, limit: int = 6) -> dict[str, Any]:
    ensure_session(session_id)
    try:
        conn = _db_conn()
        if conn is not None:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT role, content FROM messages WHERE session_id = %s ORDER BY id DESC LIMIT %s;",
                        (session_id, limit),
                    )
                    msgs = [{"role": r[0], "content": r[1]} for r in reversed(cur.fetchall())]
                    cur.execute(
                        "SELECT constraints, current_plan, pending_question, summary FROM session_state WHERE session_id = %s;",
                        (session_id,),
                    )
                    row = cur.fetchone()
            conn.close()
            state = {
                "constraints": (row[0] if row else None) or {},
                "current_plan": row[1] if row else None,
                "pending_question": row[2] if row else None,
                "summary": (row[3] if row else "") or "",
            }
            return {"messages": msgs, "state": state}
    except Exception:
        pass
    sess = _LOCAL_SESSIONS.get(session_id) or {"messages": [], "state": _default_state()}
    return {"messages": list(sess["messages"][-limit:]), "state": dict(sess["state"])}


def update_session_state(session_id: str, constraints: Optional[dict] = None,
                         current_plan: Optional[dict] = None,
                         pending_question: Optional[str] = None) -> None:
    ensure_session(session_id)
    try:
        conn = _db_conn()
        if conn is not None:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """UPDATE session_state
                           SET constraints = COALESCE(%s::jsonb, constraints),
                               current_plan = COALESCE(%s::jsonb, current_plan),
                               pending_question = %s,
                               updated_at = NOW()
                           WHERE session_id = %s;""",
                        (
                            json.dumps(constraints, ensure_ascii=False) if constraints is not None else None,
                            json.dumps(current_plan, ensure_ascii=False) if current_plan is not None else None,
                            pending_question,
                            session_id,
                        ),
                    )
            conn.close()
            return
    except Exception:
        pass
    st = _LOCAL_SESSIONS[session_id]["state"]
    if constraints is not None:
        st["constraints"] = constraints
    if current_plan is not None:
        st["current_plan"] = current_plan
    st["pending_question"] = pending_question


def get_preferences(user_key: str = "default") -> dict[str, Any]:
    try:
        conn = _db_conn()
        if conn is not None:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT language, interests, budget_band, travel_style, transportation FROM user_preferences WHERE user_key = %s;",
                        (user_key,),
                    )
                    row = cur.fetchone()
            conn.close()
            if row:
                return {
                    "language": row[0],
                    "interests": list(row[1] or []),
                    "budget_band": row[2],
                    "travel_style": row[3],
                    "transportation": row[4],
                }
    except Exception:
        pass
    return dict(_LOCAL_PREFS.get(user_key) or _default_prefs())


def update_preferences(user_key: str = "default", **kwargs) -> dict[str, Any]:
    prefs = get_preferences(user_key)
    for k in ("language", "interests", "budget_band", "travel_style", "transportation"):
        if k in kwargs and kwargs[k] is not None:
            prefs[k] = kwargs[k]
    try:
        conn = _db_conn()
        if conn is not None:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """INSERT INTO user_preferences (user_key, language, interests, budget_band, travel_style, transportation)
                           VALUES (%s, %s, %s, %s, %s, %s)
                           ON CONFLICT (user_key) DO UPDATE SET
                               language = EXCLUDED.language,
                               interests = EXCLUDED.interests,
                               budget_band = EXCLUDED.budget_band,
                               travel_style = EXCLUDED.travel_style,
                               transportation = EXCLUDED.transportation,
                               updated_at = NOW();""",
                        (user_key, prefs["language"], prefs["interests"],
                         prefs["budget_band"], prefs["travel_style"], prefs["transportation"]),
                    )
            conn.close()
            return prefs
    except Exception:
        pass
    _LOCAL_PREFS[user_key] = prefs
    return prefs


def reset_session(session_id: str) -> None:
    try:
        conn = _db_conn()
        if conn is not None:
            with conn:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM sessions WHERE session_id = %s;", (session_id,))
            conn.close()
    except Exception:
        pass
    _LOCAL_SESSIONS.pop(session_id, None)
