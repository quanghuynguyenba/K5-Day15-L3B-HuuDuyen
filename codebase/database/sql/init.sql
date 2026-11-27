CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS pois (
    id TEXT PRIMARY KEY,
    name_vi TEXT NOT NULL,
    name_en TEXT NOT NULL,
    lat DOUBLE PRECISION,
    lng DOUBLE PRECISION,
    category TEXT NOT NULL,
    tags TEXT[] NOT NULL DEFAULT '{}',
    indoor BOOLEAN NOT NULL DEFAULT FALSE,
    price_vnd INTEGER,
    open_time TEXT,
    close_time TEXT,
    closed_days TEXT[] NOT NULL DEFAULT '{}',
    visit_minutes INTEGER,
    suitable_for TEXT[] NOT NULL DEFAULT '{}',
    description_vi TEXT NOT NULL DEFAULT '',
    description_en TEXT NOT NULL DEFAULT '',
    notes_vi TEXT NOT NULL DEFAULT '',
    notes_en TEXT NOT NULL DEFAULT '',
    source TEXT NOT NULL DEFAULT '',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS poi_chunks (
    id SERIAL PRIMARY KEY,
    poi_id TEXT NOT NULL REFERENCES pois(id) ON DELETE CASCADE,
    lang TEXT NOT NULL DEFAULT 'vi',
    content TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    embedding vector(1536) NOT NULL,
    UNIQUE (poi_id, lang)
);

CREATE INDEX IF NOT EXISTS idx_poi_chunks_poi_id ON poi_chunks (poi_id);
CREATE INDEX IF NOT EXISTS idx_poi_chunks_embedding
    ON poi_chunks USING hnsw (embedding vector_cosine_ops);

-- Phase 6: Conversation memory & user preferences
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
