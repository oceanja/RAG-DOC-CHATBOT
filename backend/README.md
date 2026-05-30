# DocuPilot Backend

## Phase 0 — local setup

From the repo root, start Postgres (with pgvector) and Redis:

```bash
docker compose up -d
```

Then set up the backend:

```bash
cd backend
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

Run the API:

```bash
uvicorn app.main:app --reload
```

Verify:

```bash
curl http://localhost:8000/health
# {"status":"ok","app":"DocuPilot","environment":"development","database":"ok"}
```

The app runs `CREATE EXTENSION IF NOT EXISTS vector` on startup, so pgvector
is ready once `/health` reports `database: ok`.

## Background worker

Ingestion runs in an ARQ worker (separate process):

```bash
arq app.workers.ingest_worker.WorkerSettings
```

## Database schema: dev vs production

- **Dev:** `AUTO_CREATE_TABLES=true` (default) — tables are created from the
  models on startup. Convenient, no migration step.
- **Production:** set `AUTO_CREATE_TABLES=false` and manage schema with Alembic:

  ```bash
  alembic upgrade head      # apply migrations
  alembic revision --autogenerate -m "describe change"   # after model changes
  ```

  Alembic reads `DATABASE_URL` from app settings (see `alembic/env.py`).
  If a database already has the schema (e.g. created via create_all), mark it
  as current without re-running: `alembic stamp head`.

> **Port note:** Docker Postgres is exposed on host port **5433** to avoid
> clashing with a local Homebrew Postgres on 5432. Connect from psql with:
> `psql -h localhost -p 5433 -U docupilot -d docupilot` (password: `docupilot`).
