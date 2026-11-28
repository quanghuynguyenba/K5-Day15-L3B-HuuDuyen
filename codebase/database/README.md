# Phase 4 — PostgreSQL + pgvector Database (`codebase/database/`)

## Preferred: reuse Postgres already on port 5432 (option A)

If another pgvector Postgres is already listening on `127.0.0.1:5432` (for example container `p-121-postgres-1`), **do not** run `docker compose up` here — it will fail with `Bind for 127.0.0.1:5432 failed: port is already allocated`.

One-time setup on that shared instance (run as the existing superuser, e.g. `p121`):

```bash
docker exec -i p-121-postgres-1 psql -U p121 -d postgres -c "CREATE ROLE travel LOGIN PASSWORD 'travel';"
docker exec -i p-121-postgres-1 psql -U p121 -d postgres -c "CREATE DATABASE travel OWNER travel;"
docker exec -i p-121-postgres-1 psql -U p121 -d travel < sql/init.sql
docker exec -i p-121-postgres-1 psql -U p121 -d travel -c "GRANT ALL ON SCHEMA public TO travel; GRANT ALL ON ALL TABLES IN SCHEMA public TO travel; GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO travel;"
```

## Alternative: start this project's own container

Only if nothing else uses host port 5432:

```bash
cd codebase/database
docker compose up -d
docker compose ps
```

If 5432 is taken and you still want a dedicated container, change the host port in `docker-compose.yml` (e.g. `"5433:5432"`) and update `DATABASE_URL` accordingly.

## Configure `.env`

At the repo root:

```env
DATABASE_URL=postgresql://travel:travel@localhost:5432/travel
```

## Seed POIs and Embeddings

From the repo root:

```bash
python -m codebase.database.seed
```

This upserts all POIs from `data/pois.json` into `pois`, generates chunks (`vi` and `en`) + vector embeddings (using `EMBED_MODEL` / `API_KEY` if configured, or `local_hash` fallback), and stores them in `poi_chunks` with an HNSW cosine index.
