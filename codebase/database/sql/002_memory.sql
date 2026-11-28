-- Phase 6: Conversation Memory & User Preferences in PostgreSQL

CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,
    user_key TEXT NOT NULL DEFAULT 'default',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS messages (
    id SERIAL PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_messages_session_id ON messages (session_id, id);

CREATE TABLE IF NOT EXISTS session_state (
    session_id TEXT PRIMARY KEY REFERENCES sessions(session_id) ON DELETE CASCADE,
    constraints JSONB NOT NULL DEFAULT '{}'::jsonb,
    current_plan JSONB,
    pending_question TEXT,
    summary TEXT NOT NULL DEFAULT '',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS user_preferences (
    user_key TEXT PRIMARY KEY,
    language TEXT NOT NULL DEFAULT 'vi',
    interests TEXT[] NOT NULL DEFAULT '{}',
    budget_band TEXT NOT NULL DEFAULT '',
    travel_style TEXT NOT NULL DEFAULT '',
    transportation TEXT NOT NULL DEFAULT '',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
