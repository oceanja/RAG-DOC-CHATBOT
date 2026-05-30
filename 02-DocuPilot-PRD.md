# DocuPilot — Product Requirements Document (PRD)

> **Tagline:** *Drop a script tag on any docs site, get an AI chatbot that answers questions from your docs — with citations.*

**Project codename:** DocuPilot
**Author:** Ocean
**Document status:** Revised v2 — solo build, simplified scope
**Audience for this doc:** Solo developer (Ocean) — build blueprint

> **What changed from v1:**
> - Dropped multi-tenancy / per-tenant isolation (solo build, not a SaaS).
> - Dropped JWT signup/login → replaced with a single admin-password gate.
> - LLM provider locked to **Google Gemini (free tier)**: `gemini-2.5-flash` + `gemini-embedding-001` (768d via MRL).
> - Ingestion path: **markdown upload first**, URL crawl added later.
> - Build is **phased** (Phases 0–11) instead of week-bucketed; you can stop after any phase and still demo something.
> - Resume framing: project is "self-hostable RAG chatbot" rather than "multi-tenant SaaS."

---

## Table of Contents

1. [Overview](#1-overview)
2. [Problem Statement](#2-problem-statement)
3. [Goals & Non-Goals](#3-goals--non-goals)
4. [Target User (You)](#4-target-user-you)
5. [User Stories](#5-user-stories)
6. [Feature Scope](#6-feature-scope)
7. [UX Flows](#7-ux-flows)
8. [System Architecture](#8-system-architecture)
9. [Tech Stack & Why](#9-tech-stack--why)
10. [Data Model](#10-data-model)
11. [API Contract](#11-api-contract)
12. [The RAG Pipeline (Deep Dive)](#12-the-rag-pipeline-deep-dive)
13. [Non-Functional Requirements](#13-non-functional-requirements)
14. [Phased Build Plan](#14-phased-build-plan)
15. [Definition of Done](#15-definition-of-done)
16. [Risks & Mitigations](#16-risks--mitigations)
17. [Resume Hooks](#17-resume-hooks)
18. [Open Questions](#18-open-questions)

---

## 1. Overview

**DocuPilot** is a self-hostable RAG chatbot you can drop onto any documentation site. The owner (you) ingests a docs source — markdown upload, or a URL crawl — and gets back an embed snippet. Anyone visiting the docs site can click a chat bubble and ask natural-language questions; DocuPilot answers using the docs as the source of truth and shows clickable citations to the exact sections it pulled from.

In one sentence: **"Intercom for docs, powered by RAG, self-hosted."**

---

## 2. Problem Statement

### The pain

- Every developer-focused product has docs.
- Users **don't read docs** — they scan, get frustrated, then ask the same question in Discord/Slack/GitHub Issues for the 50th time.
- Doc-site search misses *semantically similar* questions ("how do I rate-limit?" doesn't match a page titled "Throttling configuration").
- Maintainers waste hours answering repeat questions.

### Why now

LLMs + embeddings make RAG cheap and reliable enough that a single developer can build a "talk to my docs" feature that would have required a dedicated NLP team two years ago.

### Why this is a good resume project

It hits four trending themes at once: **AI/LLM**, **RAG architecture**, **async backend engineering**, and **embeddable widgets** — all things 2026 recruiters scan resumes for.

---

## 3. Goals & Non-Goals

### Goals (MVP)

- ✅ Owner can ingest docs (markdown upload OR URL crawl) and have them ready to query in **under 5 minutes**.
- ✅ Visitors get an answer in **under 5 seconds (first token)**, streamed.
- ✅ Every AI answer includes **at least one citation** linking back to the source doc.
- ✅ The widget is embeddable on any site with **one `<script>` tag**.
- ✅ Owner can manage **multiple docs projects** under a single admin login.

### Non-goals (explicit — protects from scope creep)

- ❌ No multi-tenant SaaS. One owner (you).
- ❌ No signup flow / JWT / user accounts. A single admin password gates the dashboard.
- ❌ No payments / Stripe.
- ❌ No OAuth.
- ❌ No fine-tuning. Off-the-shelf Gemini models only.
- ❌ No multi-language (English only).
- ❌ No voice / audio.
- ❌ No conversation memory (each chat is stateless).
- ❌ No teams / per-user permissions.

---

## 4. Target User (You)

The primary user is **you**, the developer, hosting DocuPilot for your own docs (or a friend's, or an OSS project you maintain).

Secondary user is the **visitor on the docs site** — the person who clicks the chat bubble and asks a question. They don't sign up, don't have an account, and never see the dashboard.

(The PRD's earlier persona section is dropped — this is a personal tool, not a market-fit product.)

---

## 5. User Stories

### Owner stories (you, behind the admin login)

1. As the **owner**, I want to **log in with a single admin password**, so that I can manage projects without building a full auth system.
2. As the **owner**, I want to **create a project** (e.g., "ReactKit Docs"), so that I can have separate bots for separate docs sources.
3. As the **owner**, I want to **upload a markdown file** OR **submit a docs URL**, so that I can choose the ingestion path that fits the source.
4. As the **owner**, I want to **see ingestion status** (pending / embedding / ready / failed), so that I know when my bot is live.
5. As the **owner**, I want to **copy an embed snippet**, so that I can paste it into my docs site.
6. As the **owner**, I want to **see a list of questions visitors have asked**, so that I learn what my docs don't explain well.
7. As the **owner**, I want to **re-ingest** when docs change, so that the bot stays current.

### Visitor stories (anyone on the docs site)

8. As a **visitor**, I want to **click a chat bubble in the corner**, so that I can ask without leaving the page.
9. As a **visitor**, I want **answers to stream as they generate**, so that I don't sit staring at a spinner.
10. As a **visitor**, I want to **see source links under each answer**, so that I can verify and read more.
11. As a **visitor**, I want the bot to **say "I don't know" honestly**, so that I can trust it when it does answer.

---

## 6. Feature Scope

### MVP (must-have)

| # | Feature | Why it's MVP |
|---|---------|-------------|
| F1 | Admin-password gate (single password, env-var) | Need *some* lock once deployed; full auth is overkill |
| F2 | Create / list / delete projects | Owner's main object |
| F3 | Ingest docs from markdown upload | Simplest onboarding path |
| F4 | Ingest docs from a URL (sitemap crawl) | Added after markdown is working |
| F5 | Async background job for chunking + embedding | Ingestion must not block the API |
| F6 | Chat API with RAG + SSE streaming | The core product |
| F7 | Citations in every response | Trust + differentiation |
| F8 | Embeddable JS widget (vanilla, <30KB) | Distribution mechanism |
| F9 | Owner dashboard (project list, ingestion status, embed snippet) | Owner workflow |
| F10 | Question log (last 100 questions per project) | Closes the feedback loop |

### Nice-to-have (post-MVP)

- Thumbs up/down on answers + storage of feedback
- Incremental re-ingestion (only changed pages)
- Custom widget colors + brand name
- Basic analytics (questions/day, top topics, "I don't know" rate)

### Out of Scope (explicit)

- ❌ Multi-tenancy / per-project API keys
- ❌ Signup / user accounts / JWT
- ❌ Stripe / billing
- ❌ OAuth (Google/GitHub login)
- ❌ Confluence / Notion / Slack integrations
- ❌ Per-visitor conversation history
- ❌ Fine-tuning / custom models
- ❌ Mobile app

---

## 7. UX Flows

### Flow 1: Owner onboards a docs source

```
1. Open the deployed dashboard URL → admin login screen
2. Enter admin password → land on dashboard
3. Click "Create project" → modal with name + optional docs URL
4. Submit → project created, status = "pending"
5. On project detail page, upload markdown OR trigger URL crawl
6. Status transitions: pending → embedding → ready
7. Owner sees embed snippet → copies it
8. Owner sees a "Try it" preview widget on the dashboard
```

### Flow 2: Visitor asks a question

```
1. Visitor on docs site → sees chat bubble (bottom-right)
2. Clicks bubble → widget expands
3. Types "How do I set up authentication?" → presses Enter
4. Widget shows "..." (typing indicator)
5. Server streams response token-by-token → widget renders incrementally
6. After response: citations appear as small clickable cards
7. Visitor clicks a citation → opens the source doc page in a new tab
```

### Flow 3: Owner reviews questions

```
1. Owner opens dashboard → clicks project name
2. Sees "Recent Questions" tab → list of last 100 with timestamps
3. Clicks a question → sees the answer + which citations were used
```

---

## 8. System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│   Site visitor's browser                Owner's browser         │
│   ┌──────────────┐                      ┌────────────────┐      │
│   │ Embed widget │                      │ React dashboard│      │
│   └──────┬───────┘                      └────────┬───────┘      │
│          │ chat over SSE                         │ REST +       │
│          │ (public, project_id)                  │ admin token  │
└──────────┼─────────────────────────────────────────┼────────────┘
           │                                       │
           ▼                                       ▼
   ┌──────────────────────────────────────────────────────────┐
   │                   FastAPI Backend                        │
   │  ┌────────────┐  ┌────────────┐  ┌──────────┐  ┌───────┐│
   │  │ Admin gate │  │ Projects   │  │ Chat     │  │ Logs  ││
   │  │ /admin     │  │ /projects  │  │ /chat    │  │       ││
   │  └────────────┘  └─────┬──────┘  └────┬─────┘  └───────┘│
   │                        │              │                 │
   │                  ┌─────▼──────────────▼─────┐           │
   │                  │   Service layer          │           │
   │                  │   (ingest, retrieve)     │           │
   │                  └────┬───────────┬─────────┘           │
   └───────────────────────┼───────────┼─────────────────────┘
                           │           │
              ┌────────────▼─┐    ┌────▼─────────────────┐
              │  PostgreSQL  │    │  Gemini API          │
              │  + pgvector  │    │  - embeddings        │
              │              │    │  - chat completions  │
              │  - projects  │    └──────────────────────┘
              │  - documents │
              │  - chunks(v) │
              │  - questions │
              └──────────────┘
                      ▲
                      │
        ┌─────────────┴─────────────┐
        │ ARQ background worker     │
        │ (Redis-backed)            │
        │ - crawl URL (Phase 7)     │
        │ - chunk text              │
        │ - embed chunks            │
        │ - store with pgvector     │
        └───────────────────────────┘
```

### Key architectural decisions

| Decision | Choice | Reasoning |
|----------|--------|-----------|
| Vector store | **pgvector** (Postgres extension) | One DB to run, free, fast for <1M chunks. |
| Background jobs | **ARQ** (Redis-backed) | Simpler than Celery, async-native, fits FastAPI. |
| Streaming protocol | **SSE** | One-way is enough; simpler than WebSocket. |
| Owner auth | **Single admin password (env var)** | Solo build — full JWT/signup is overkill. ~10 lines vs ~80. |
| Visitor auth | **None — `project_id` in URL** | Widget is public; project_id alone scopes retrieval. |
| Dashboard | **React + Vite + Tailwind** | Standard, fast, familiar. |
| Embed widget | **Vanilla JS, no framework, Shadow DOM** | Must be tiny (<30KB) and not clash with host CSS. |

---

## 9. Tech Stack & Why

### Backend

| Tech | Purpose | Why |
|------|---------|-----|
| **Python 3.11+** | Language | Best LLM/ML ecosystem |
| **FastAPI** | Web framework | Async + Pydantic + auto-docs |
| **uvicorn** | ASGI server | Standard with FastAPI |
| **SQLAlchemy 2.0 (async)** | ORM | Reuse patterns from SkyVoice |
| **PostgreSQL 16 + pgvector** | DB + vectors | One process, no separate vector DB |
| **Redis** | Job queue substrate | Standard async job backing store |
| **ARQ** | Background jobs | Async-native, FastAPI-friendly |
| **httpx** | HTTP client | Async, for URL crawling |
| **BeautifulSoup4** | HTML parsing | Clean text from crawled pages |
| **markdown-it-py** | Markdown parsing | Handles uploaded `.md` files |
| **google-genai** | LLM client | Gemini Flash + embeddings (free tier) |
| **tiktoken** | Token counting | For chunk sizing |
| **pydantic-settings** | Config | Same pattern as SkyVoice |

*Dropped from v1:* `PyJWT`, `passlib[bcrypt]` (no longer needed — admin password is a simple string compare against env var).

### Frontend (Dashboard)

| Tech | Purpose | Why |
|------|---------|-----|
| **React 18+** | UI | What you know |
| **Vite** | Build tool | Fast dev |
| **TailwindCSS** | Styling | Quick polished UI |
| **React Router** | Routing | Standard |
| **axios** | HTTP client | Standard |

### Frontend (Embed Widget)

| Tech | Purpose | Why |
|------|---------|-----|
| **Vanilla TypeScript** | Widget logic | No React dep → <30KB |
| **Vite (lib mode)** | Build | Outputs a single IIFE script |
| **Shadow DOM** | Style isolation | Prevents clashes with host site CSS |

### Infra (Phase 11)

- **Railway** or **Fly.io** for backend
- **Supabase** free tier for Postgres+pgvector (managed, one-click)
- **Upstash** free tier for Redis (or Railway add-on)
- **Vercel** for dashboard
- Widget JS served from backend `/widget.js` with long Cache-Control

---

## 10. Data Model

```sql
-- A "project" = one chatbot instance (one docs source)
CREATE TABLE projects (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name             TEXT NOT NULL,
    docs_url         TEXT,
    status           TEXT NOT NULL DEFAULT 'pending',
                     -- pending | crawling | embedding | ready | failed
    last_ingested_at TIMESTAMPTZ,
    error_message    TEXT,
    created_at       TIMESTAMPTZ DEFAULT NOW(),
    updated_at       TIMESTAMPTZ DEFAULT NOW()
);

-- A "document" = one source page (one URL, one section of an uploaded file)
CREATE TABLE documents (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id   UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    source_url   TEXT,         -- nullable for uploads
    title        TEXT NOT NULL,
    content      TEXT NOT NULL,
    created_at   TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_documents_project ON documents(project_id);

-- A "chunk" = a small piece of a document, with its embedding
CREATE TABLE chunks (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id   UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    document_id  UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index  INT NOT NULL,
    content      TEXT NOT NULL,
    embedding    VECTOR(768),   -- Gemini embedding (MRL-truncated from 3072d)
    created_at   TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_chunks_project ON chunks(project_id);

-- pgvector index for fast similarity search
CREATE INDEX idx_chunks_embedding ON chunks
USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- A "question" = one chat interaction (Phase 10)
CREATE TABLE questions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id      UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    question_text   TEXT NOT NULL,
    answer_text     TEXT NOT NULL,
    cited_chunk_ids UUID[] NOT NULL,
    visitor_ip_hash TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_questions_project_created ON questions(project_id, created_at DESC);
```

### Notes

- **No `users` table.** Owner = admin password (env var). No `owner_id` on projects.
- **No `api_key` column.** Widget identifies a project by `project_id` in the URL — fine because there's no multi-tenant data to protect.
- **Cascading deletes everywhere** — delete a project, all its chunks/questions go with it.
- **`visitor_ip_hash`** — never store raw IPs (privacy). SHA256 with a server-side salt.

---

## 11. API Contract

### Admin endpoints (require admin token)

| Method | Path | Purpose | Request | Response |
|--------|------|---------|---------|----------|
| POST | `/api/admin/login` | Exchange password for token | `{password}` | `{token}` |
| GET | `/api/projects` | List all projects | — | `[{id, name, status, ...}]` |
| POST | `/api/projects` | Create project | `{name, docs_url?}` | `{id, name, status}` |
| GET | `/api/projects/{id}` | Get project detail | — | `{id, name, status, embed_snippet, ...}` |
| DELETE | `/api/projects/{id}` | Delete project | — | `204` |
| POST | `/api/projects/{id}/ingest` | Trigger ingestion | `{type: "url" \| "markdown", url?, content?}` | `{job_id, status}` |
| GET | `/api/projects/{id}/questions` | List recent questions | `?limit=100` | `[{question, answer, citations, created_at}]` |

Auth header: `Authorization: Bearer <admin_token>` (returned by `/api/admin/login`).

### Public widget endpoint (no auth)

| Method | Path | Purpose | Request | Response |
|--------|------|---------|---------|----------|
| POST | `/api/chat` | Ask a question | `{project_id, question}` | **SSE stream**: `data: {"type":"token","text":"..."}\n\n` per token, then `data: {"type":"citations","items":[...]}\n\n`, then `data: [DONE]` |

### Public meta endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/widget.js` | The embed script (cached aggressively) |
| GET | `/health` | Health check |

---

## 12. The RAG Pipeline (Deep Dive)

Two distinct pipelines: **ingestion** (offline, async) and **retrieval+generation** (online, per-question).

### Pipeline A: Ingestion (background job)

```
[Owner triggers ingestion — markdown upload OR URL]
        │
        ▼
1. Update project.status = "embedding" (or "crawling" for URLs)
        │
        ▼
2. Fetch docs:
   - Markdown mode: parse uploaded markdown → split by H1 → list of "pages"
   - URL mode (Phase 7): fetch sitemap.xml → list of URLs → fetch each → BeautifulSoup → extract text
        │
        ▼
3. For each page, create a `documents` row.
        │
        ▼
4. For each document, chunk the text:
   - Target chunk size: ~500 tokens (tiktoken)
   - Overlap: ~50 tokens (preserves context across boundaries)
   - Recursive splitter (paragraph → sentence → words)
        │
        ▼
5. Batch-embed chunks (100 per Gemini API call)
        │
        ▼
6. Insert chunks with embeddings into `chunks` table.
        │
        ▼
7. Update project.status = "ready", last_ingested_at = NOW()
```

**Failure handling:**
- If crawl fails: status = "failed", error_message set, surfaced in dashboard.
- If embed API fails mid-batch: retry with exponential backoff (3 tries).
- Still failing: status = "failed", partial chunks left in place so re-ingest can resume.

### Pipeline B: Retrieval + Generation (per question)

```
[Visitor types question, widget POSTs /api/chat]
        │
        ▼
1. Resolve project_id from request body, look up project (404 if missing)
        │
        ▼
2. Embed the question (one Gemini call)
        │
        ▼
3. Vector search:
   SELECT * FROM chunks
   WHERE project_id = :pid
   ORDER BY embedding <=> :question_embedding
   LIMIT 5
        │
        ▼
4. Build prompt:
   "You are a helpful assistant for [project name]. Answer using ONLY the
    context below. If the answer isn't in the context, say 'I don't know'.
    Cite sources by [1], [2], etc.

    Context:
    [1] {chunk1_content}
    [2] {chunk2_content}
    ...

    Question: {user_question}"
        │
        ▼
5. Stream completion from Gemini, SSE-forwarding tokens to widget.
        │
        ▼
6. After stream completes, send a final SSE event with citation data:
   data: {"type": "citations", "items": [{id, title, url, snippet}, ...]}
        │
        ▼
7. Async: insert into `questions` table for the dashboard.
```

### Key RAG decisions (interview gold)

- **Why top-5 chunks?** Balance between context richness and prompt cost / latency. Too much dilutes focus.
- **Why ~500 tokens per chunk with 50-token overlap?** Standard heuristic. Big enough to contain a coherent thought, small enough to combine multiple chunks without blowing the context window.
- **Why cosine similarity?** Standard for embedding similarity. pgvector supports it via the `<=>` operator.
- **Why force "I don't know"?** Without it, the LLM hallucinates. The system prompt explicitly grounds it in the retrieved context.
- **Why 768d embeddings, not 3072d?** Gemini's MRL truncation gives near-identical retrieval quality at a quarter of the index size and within pgvector ivfflat's 2000d limit.

---

## 13. Non-Functional Requirements

| Category | Requirement |
|----------|-------------|
| **Performance** | Chat: first-token latency < 1.5s (p95). Full response < 5s. |
| **Performance** | Ingestion: 100-page site fully ingested in < 5 min. |
| **Availability** | Best effort (personal tool — no SLA). |
| **Security** | Admin password compared in constant time, stored only as env var. Token expiry 7 days. |
| **Privacy** | No PII from visitors stored. IPs hashed. Question text retained. |
| **Cost** | Gemini free tier covers dev + demo. Hard monthly cap configured. |
| **Observability** | Structured JSON logs. Request ID per request. Latency log line for `/api/chat`. |
| **Widget size** | < 30KB gzipped. |
| **Browser support** | Last 2 versions of Chrome, Firefox, Safari, Edge. |

---

## 14. Phased Build Plan

Each phase ships a runnable, testable slice. After Phase 5 you have a working RAG demo. Phases 6–11 add capability + polish.

### Phase 0 — Repo + Local Infra
- Folder structure (`backend/`, `frontend/`, `widget/`).
- `docker-compose.yml`: pgvector + redis.
- `backend/pyproject.toml`, `backend/app/main.py` with `/health`, `config.py`, `database.py`.
- **Done when:** `docker compose up` + uvicorn → `/health` 200; `CREATE EXTENSION vector` succeeds.

### Phase 1 — Data Model
- SQLAlchemy models: `Project`, `Document`, `Chunk`. (No `users`, no `api_key`.)
- `Base.metadata.create_all()` on startup. Pgvector cosine index.
- Seed one default project.
- **Done when:** Tables exist; one project visible.

### Phase 2 — Ingestion (markdown, synchronous)
- `utils/chunking.py` — recursive splitter, ~500 tokens, 50 overlap.
- `services/llm.py` — Gemini wrapper (`embed_batch`, `chat_stream`).
- `services/ingestion.py` — `ingest_markdown(project_id, raw_md)`.
- `POST /api/projects/{id}/ingest/markdown`.
- **Done when:** Curl POST → chunks visible in DB with non-zero embeddings.

### Phase 3 — Retrieval + Chat (non-streaming)
- `services/retrieval.py` — top-K vector search.
- `services/chat.py` — prompt building + Gemini call.
- `POST /api/chat` → JSON `{answer, citations}`.
- **Done when:** Curl returns cited answer; off-topic questions → "I don't know."

### Phase 4 — SSE Streaming
- Convert `/api/chat` to `StreamingResponse`.
- SSE protocol: tokens, then citations, then `[DONE]`.
- CORS middleware.
- **Done when:** `curl -N` shows incremental tokens.

### Phase 5 — Embeddable Widget
- Vite lib mode → IIFE `widget.js`.
- Shadow-DOM-isolated bubble + chat panel.
- SSE via `fetch` + `ReadableStream`.
- Minimal markdown renderer. Citation cards.
- `widget/demo.html` for local testing.
- Backend serves built bundle at `/widget.js`.
- **Done when:** Demo page → ask question → streamed cited answer. Gzipped bundle < 30KB.

> **Checkpoint:** After Phase 5 you have a demoable RAG chatbot.

### Phase 6 — Background Jobs (ARQ)
- Move ingestion into an ARQ task.
- Status state machine: `pending → embedding → ready | failed`.
- 3× exponential backoff retries on Gemini errors.
- **Done when:** Large upload returns fast; status transitions correctly.

### Phase 7 — URL Crawling
- `utils/crawling.py` — sitemap parsing + page fetching (BeautifulSoup).
- New worker task `ingest_url`.
- Unify endpoint: `POST /api/projects/{id}/ingest` with `{type, url?, content?}`.
- Respect `robots.txt`. Cap 200 pages.
- **Done when:** Submit real docs site → ingested → cited answer on a real question.

### Phase 8 — Owner Dashboard (no auth yet)
- Vite + React + Tailwind + React Router.
- Pages: project list, project detail (ingest form, status polling, embed snippet, "Try it" widget).
- **Done when:** Click-through: create → ingest → ready → copy snippet → widget works.

### Phase 9 — Admin Password Gate
- `POST /api/admin/login` → token.
- `require_admin` dependency on `/api/projects*` routes.
- `/api/chat` + `/widget.js` stay **public**.
- Frontend login page + axios interceptor.
- **Done when:** Logged out → 401 on dashboard routes; widget still works publicly.

### Phase 10 — Question Log + Polish
- `questions` table.
- Async insert after each chat completes (FastAPI `BackgroundTasks`).
- `GET /api/projects/{id}/questions?limit=100`.
- Dashboard: "Recent Questions" tab.
- Polish: skeletons, toasts, empty states, delete confirm, re-ingest.
- Adopt Alembic (schema is stable now).
- **Done when:** 10 widget questions appear in dashboard with citations.

### Phase 11 — Deployment + README + Demo Video
- Backend → Railway / Fly.io.
- Postgres+pgvector → Supabase free tier.
- Redis → Upstash free tier.
- Frontend → Vercel.
- README with live demo link, architecture diagram, tech rationale, dev instructions.
- 60-second Loom demo.
- LinkedIn / blog post.
- **Done when:** Open live URL from a different network → full flow works.

---

## 15. Definition of Done

- ✅ Deployed live (backend + DB + dashboard) on a public URL
- ✅ End-to-end demo works without you touching the keyboard
- ✅ README explains: what it is, how to use it, architecture, tech choices
- ✅ A 60-second demo video
- ✅ Source on GitHub with clean commit history
- ✅ At least 1 real docs site ingested and answering questions

---

## 16. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Gemini free tier rate-limits during dev | Med | Med | Fall back to `sentence-transformers` (all-MiniLM-L6-v2, 384d, local) for embeddings; keep Gemini for chat only. |
| Hallucinations damage trust | High | High | Strong "use only context" system prompt. Force citations. Test with adversarial questions. |
| Widget breaks host site styling | Med | Med | Shadow DOM isolation. Test on real sites. |
| Scope creep, project never ships | **High** | **High** | This PRD locks scope. Anything outside Section 6 MVP → deferred. |
| Gemini model deprecated mid-build | Low | Med | Model name in env config, not hardcoded. |
| Crawling other sites' docs raises legal concern | Low | High | Only ingest docs you own or that are clearly public (sitemap published). Respect `robots.txt`. |
| Ingestion job hangs / Redis dies | Low | Med | Job timeouts, status = "failed" after N minutes. |

---

## 17. Resume Hooks

How to describe this on your resume after shipping:

### Bullet 1 (architecture)
> Built **DocuPilot**, a self-hostable RAG chatbot that embeds on any docs site via a `<script>` tag. FastAPI + PostgreSQL + pgvector + ARQ workers + SSE streaming. Vector retrieval over <X>K chunks across <Y> projects.

### Bullet 2 (impact)
> Reduced repeat documentation questions for <X> early users by enabling natural-language search with cited answers; achieved sub-1.5s first-token latency via SSE streaming.

### Bullet 3 (engineering)
> Designed end-to-end async ingestion pipeline (crawl → chunk → embed → store with pgvector cosine search) with retry/recovery handling; built a <30KB vanilla-JS embeddable widget with Shadow DOM isolation.

### Bullet 4 (full-stack)
> Built React + Tailwind admin dashboard with ingestion status polling, question analytics, and one-click embed snippet generation. Deployed full stack to Railway + Vercel.

### Interview talking points

- **"Why RAG and not fine-tuning?"** — Fine-tuning is expensive, slow to update, and overkill for docs. RAG lets you update by re-ingesting, costs only the embedding + retrieval, and gives you citations for free.
- **"Why pgvector instead of Pinecone?"** — Cost (free), one DB to run, sufficient scale. Trade-off: less performant at >10M vectors. For sub-1M, pgvector wins on simplicity.
- **"How did you prevent hallucinations?"** — Strict system prompt, "I don't know" instruction, force citations from provided context only, low temperature.
- **"Why a single admin password instead of full auth?"** — It's a self-hosted personal tool, not a SaaS. A single env-var password gives the security I need (gate the dashboard once deployed) without spending engineering time on signup flows, password reset, JWT rotation, etc. that nobody would use.
- **"What was the hardest part?"** — Pick one and have a real story: SSE streaming through CORS, chunking strategy, widget bundle size, Shadow DOM event handling, etc.

---

## 18. Open Questions

1. **Embedding fallback:** Gemini embeddings or local `sentence-transformers`? **Recommendation:** start with Gemini, switch only if rate-limited.
2. **Where to host Postgres?** Railway or Supabase? **Recommendation:** Supabase free tier — pgvector pre-installed.
3. **Widget bundling:** IIFE or ES module? **Recommendation:** IIFE — works in every embed scenario.
4. **Crawler smartness:** sitemap-only, or follow links? **Recommendation:** sitemap-only for MVP. Document the limitation.
5. **Conversation memory:** stateless or remember last 3 turns? **Recommendation:** stateless. Saves complexity. Add later if needed.

---

## Appendix A: File Structure

```
docupilot/
├── README.md
├── docker-compose.yml          # postgres + redis for local dev
├── 02-DocuPilot-PRD.md         # this file
├── backend/
│   ├── pyproject.toml
│   ├── app/
│   │   ├── main.py             # FastAPI app
│   │   ├── config.py           # pydantic-settings
│   │   ├── database.py         # async session
│   │   ├── dependencies.py     # require_admin
│   │   ├── models/             # SQLAlchemy models
│   │   ├── schemas/            # Pydantic request/response
│   │   ├── routers/
│   │   │   ├── admin.py        # password login
│   │   │   ├── projects.py
│   │   │   └── chat.py
│   │   ├── services/
│   │   │   ├── ingestion.py    # chunk + embed
│   │   │   ├── retrieval.py    # vector search
│   │   │   ├── llm.py          # Gemini wrapper
│   │   │   └── chat.py         # RAG prompt + answer
│   │   ├── workers/
│   │   │   └── ingest_worker.py # ARQ worker
│   │   └── utils/
│   │       ├── chunking.py
│   │       └── crawling.py
│   └── tests/
├── frontend/                    # React dashboard
│   ├── package.json
│   ├── vite.config.ts
│   └── src/
│       ├── App.tsx
│       ├── routes/
│       ├── pages/
│       ├── components/
│       └── api/
└── widget/                      # Embeddable JS widget
    ├── package.json
    ├── vite.config.ts
    ├── demo.html
    └── src/
        ├── widget.ts
        └── styles.ts
```

---

## Appendix B: Useful References

- **FastAPI:** https://fastapi.tiangolo.com/
- **pgvector:** https://github.com/pgvector/pgvector
- **ARQ (Async Redis Queue):** https://arq-docs.helpmanual.io/
- **Google Gemini API:** https://ai.google.dev/gemini-api/docs
- **Gemini embeddings (MRL):** https://ai.google.dev/gemini-api/docs/embeddings
- **Server-Sent Events spec:** https://html.spec.whatwg.org/multipage/server-sent-events.html
- **Anthropic's "Building effective agents":** https://www.anthropic.com/engineering/building-effective-agents

---

## Sign-off

This PRD locks the simplified solo-build scope. Anything outside Section 6 (MVP table) is deferred. Build phase by phase per Section 14; you have a demoable artifact after Phase 5.
