# DocuPilot

> Drop a `<script>` tag on any docs site, get an AI chatbot that answers
> questions from your docs — with citations.

**Live demo:** [rag-doc-chatbot.vercel.app](https://rag-doc-chatbot.vercel.app/) · **Backend:** [docupilot-41e2.onrender.com](https://docupilot-41e2.onrender.com/health) · **▶ 60-second walkthrough:** [watch on Google Drive](https://drive.google.com/file/d/1afnhjF8k1XhG_3lDAJlug01CuEErdjWC/view?usp=sharing)

> Note: the backend runs on Render's free tier and sleeps after 15 min idle — the **first** load may take ~40 s to wake up. After that, requests are instant.

DocuPilot is a self-hostable RAG chatbot. The owner ingests documentation
(markdown upload or sitemap crawl), the visitor opens a chat bubble on the
docs site and asks questions, and the bot streams answers grounded only in
the indexed docs with clickable citations back to the source pages.

```
> "What does hx-boost do?"
[1] hx-boost converts <a>/<form> tags to AJAX… [more]
    [1] https://htmx.org/attributes/hx-boost/
    [2] https://htmx.org/attributes/hx-inherit/
```

## Numbers worth knowing

| Metric | Value |
|---|---|
| Widget bundle (gzipped) | **3.4 KB** |
| Embedding dimension | 768 (Gemini MRL-truncated from 3072) |
| Chunk size / overlap | ~500 tokens / 50 tokens |
| Retrieval top-K | 5 |
| Vector search | pgvector ivfflat, cosine distance |
| Chat first-token latency | < 1.5 s (p95) |
| Backend tests | **18 passing** (pytest) |

## Highlights

- **Embeddable widget** — vanilla TS, Shadow-DOM isolated, **~3.4 KB gzipped**
- **Retrieval-Augmented Generation** with Google Gemini (`gemini-2.5-flash`
  for chat + `gemini-embedding-001` MRL-truncated to 768d)
- **PostgreSQL + pgvector** for chunk storage and cosine-distance search
- **Async ingestion** via ARQ (Redis-backed): markdown upload or sitemap crawl
- **SSE streaming** of answers token-by-token
- **Admin dashboard** (React + Vite + Tailwind) — projects, ingest, embed snippet,
  Recent Questions tab with citations
- **HMAC-signed admin tokens** — no JWT dependency

## Architecture

```
                Visitor browser                Owner browser
                ┌──────────────┐               ┌────────────────┐
                │ Embed widget │               │ React dashboard│
                └──────┬───────┘               └────────┬───────┘
                       │ SSE /api/chat                  │ REST + Bearer token
                       │ (public, project_id)           │ (admin password)
                       ▼                                ▼
              ┌──────────────────────────────────────────────┐
              │                FastAPI                       │
              │  admin · projects · chat · widget.js · health│
              └─────┬──────────────┬───────────────┬─────────┘
                    │              │               │
            ┌───────▼─────┐  ┌─────▼─────┐  ┌──────▼──────┐
            │ Postgres +  │  │  Redis    │  │ Gemini API  │
            │ pgvector    │  │           │  │ (embed+chat)│
            │ projects /  │  │ ARQ queue │  └─────────────┘
            │ documents / │  └─────┬─────┘
            │ chunks /    │        │
            │ questions   │        ▼
            └─────────────┘   ┌──────────────┐
                              │ ARQ worker   │
                              │ - crawl URL  │
                              │ - chunk text │
                              │ - embed      │
                              │ - store      │
                              └──────────────┘
```

## Tech choices, briefly

| Choice | Why |
|---|---|
| **pgvector** | One DB to run, free, sufficient at <1M chunks |
| **ARQ** | Async-native, simpler than Celery, fits FastAPI |
| **Gemini** | Free tier covers dev + demo; MRL embeddings → 768d fit pgvector ivfflat |
| **SSE** | One-way streaming; simpler than WebSocket |
| **Admin password (HMAC token)** | Solo build — full JWT/signup is overkill |
| **Vanilla TS widget + Shadow DOM** | Tiny bundle, no host-CSS clashes |

Full RAG rationale, NFRs, and risks live in [02-DocuPilot-PRD.md](./02-DocuPilot-PRD.md).

## Local development

Requires Docker, Python 3.11+, Node 20+.

```bash
# 1. Start Postgres (pgvector) + Redis
docker compose up -d

# 2. Backend
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
# add your GEMINI_API_KEY to .env
uvicorn app.main:app --reload     # terminal A

# 3. ARQ worker (separate process)
arq app.workers.ingest_worker.WorkerSettings   # terminal B

# 4. Dashboard
cd ../frontend
npm install
cp .env.example .env
npm run dev                       # terminal C — http://localhost:5173

# 5. Widget (build once; backend serves /widget.js from widget/dist/)
cd ../widget && npm install && npm run build
```

Default admin password is `change-me` (set in `.env`). The dashboard
gates everything behind it; the chat bubble is public.

## API surface

| Method | Path | Auth | Purpose |
|---|---|---|---|
| POST | `/api/admin/login` | — | Exchange password for token (7d) |
| GET | `/api/projects` | admin | List projects |
| POST | `/api/projects` | admin | Create project |
| GET | `/api/projects/{id}` | admin | Project detail + embed snippet |
| DELETE | `/api/projects/{id}` | admin | Delete project (cascades) |
| POST | `/api/projects/{id}/ingest` | admin | Enqueue ingest `{type:"markdown"\|"url", …}` |
| GET | `/api/projects/{id}/questions` | admin | Recent Q&A with hydrated citations |
| POST | `/api/chat` | **public** | SSE stream of tokens + citations |
| GET | `/widget.js` | **public** | The embed script |
| GET | `/health` | — | DB ping + project count |

## Deployment

See [DEPLOY.md](./DEPLOY.md) for step-by-step on Railway + Supabase + Upstash + Vercel.

## Repo layout

```
.
├── backend/        FastAPI + ARQ worker + Alembic
├── frontend/       React dashboard
├── widget/         Embeddable vanilla-TS chat widget
├── scripts/        init-pgvector.sql
├── Dockerfile      Multi-stage: builds widget, serves backend
├── docker-compose.yml
└── 02-DocuPilot-PRD.md
```
