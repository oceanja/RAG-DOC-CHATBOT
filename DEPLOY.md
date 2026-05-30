# Deploying DocuPilot

This walks through a free-tier deploy: **Supabase** (Postgres+pgvector),
**Upstash** (Redis), **Railway** (backend + worker), **Vercel** (dashboard).
Adjust if you prefer Fly.io / Render / etc.

The end state: open the live dashboard URL from a different machine →
log in → ingest a docs site → ask a question via the widget → cited answer.

> Estimated cost: $0/month at low traffic. Gemini free tier covers dev + demo.

---

## 0. Prerequisites

- A GitHub repo containing this project
- Accounts: Supabase, Upstash, Railway, Vercel, Google AI Studio
- A long random string for `ADMIN_PASSWORD` and another for `IP_HASH_SALT`
  (e.g. `openssl rand -hex 32`)

---

## 1. Postgres + pgvector — Supabase

1. New project → wait for it to provision.
2. Project Settings → **Database** → enable extension **`vector`**.
3. Copy the **Connection string (Transaction pooler)** URL.
   - Replace the prefix `postgres://` with `postgresql+asyncpg://`.
   - This becomes `DATABASE_URL`.

---

## 2. Redis — Upstash

1. Create a database (any free region close to your Railway region).
2. Copy the `rediss://default:<token>@<host>:6379` URL.
   - This becomes `REDIS_URL`. (Upstash uses TLS — the `rediss://` scheme is correct.)

---

## 3. Gemini API key

1. https://aistudio.google.com/apikey → **Create API key**.
2. This becomes `GEMINI_API_KEY`.

---

## 4. Backend + worker — Railway

Railway deploys **two services from the same repo**, sharing the Dockerfile
at the repo root. One serves HTTP; the other runs the ARQ worker.

### 4a. Web service

1. New project → **Deploy from GitHub repo** → pick your DocuPilot repo.
2. Service settings:
   - **Dockerfile path:** `Dockerfile` (root)
   - **Build context:** `/` (repo root)
3. Variables (Settings → Variables):

   ```
   ENVIRONMENT=production
   DEBUG=false
   AUTO_CREATE_TABLES=false
   DATABASE_URL=postgresql+asyncpg://…       # from Supabase
   REDIS_URL=rediss://default:…@…:6379       # from Upstash
   GEMINI_API_KEY=…
   ADMIN_PASSWORD=<long random>
   IP_HASH_SALT=<long random>
   PUBLIC_BASE_URL=https://<this-railway-service>.up.railway.app
   CORS_ORIGINS=["https://<dashboard>.vercel.app"]
   ```

4. Generate a public domain (Settings → Networking → Generate domain).
   Use that domain to fill in `PUBLIC_BASE_URL` (then redeploy so the change
   takes effect, or set it before generating the domain if you know the slug).

5. Deploy. On first boot the start command runs `alembic upgrade head` to
   create tables, then `uvicorn`.

### 4b. Worker service

1. In the same Railway project → **+ New** → **Empty service** → connect the
   same repo (same Dockerfile).
2. Variables: **link the same variables as the web service** (Railway lets you
   share via Shared Variables, or paste them).
3. **Custom start command:**

   ```
   arq app.workers.ingest_worker.WorkerSettings
   ```

4. No public domain needed (worker only talks to Redis + Postgres + Gemini).

> Verify both services are happy: web service `/health` returns 200,
> worker logs show `Starting worker for 2 functions: ingest_markdown_job, ingest_url_job`.

---

## 5. Dashboard — Vercel

1. **Add New → Project** → import the same repo.
2. **Root directory:** `frontend`
3. **Framework preset:** Vite (auto-detected)
4. **Build command:** `npm run build` · **Output:** `dist`
5. **Environment Variable:**

   ```
   VITE_API_BASE=https://<railway-web-service>.up.railway.app
   ```

6. Deploy.

Once Vercel gives you a domain, add it to the backend's `CORS_ORIGINS`
(comma-style JSON array — see env template) and redeploy the backend so
browser calls aren't blocked.

---

## 6. Smoke test

```bash
# from any machine
curl https://<backend>/health
# {"status":"ok","database":"ok",...}

curl -X POST https://<backend>/api/admin/login \
  -H 'content-type: application/json' \
  -d '{"password":"<your-admin-password>"}'
# {"token":"..."}
```

Then in a browser:

1. Open `https://<dashboard>.vercel.app/` → login.
2. Create a project → URL-crawl a public docs site.
3. Wait for `ready`, copy the embed snippet, paste it into any HTML file:

   ```html
   <script src="https://<backend>/widget.js"
           data-project-id="…"
           data-api-base="https://<backend>"></script>
   ```

4. Open that HTML, click the bubble, ask a question. Cited answer should stream in.

---

## Common gotchas

- **`role "..." does not exist`** at boot — your `DATABASE_URL` is pointing at
  the wrong DB. Re-check the connection string from Supabase.
- **CORS errors in the browser console** — the docs site origin or dashboard
  origin isn't in `CORS_ORIGINS`. Add it and redeploy.
- **Widget loads but `/api/chat` returns CORS** — same as above, but check that
  `allow_credentials=False` (default in our config) matches the wildcard / list.
- **Embed snippet shows `localhost`** — `PUBLIC_BASE_URL` wasn't set on the
  backend. Set it and redeploy; existing snippets re-render correctly on next
  dashboard load.
- **Worker stuck enqueued, never picks up** — worker service didn't start. Check
  its Railway logs.
- **Migrations didn't run** — the Dockerfile's CMD includes `alembic upgrade head`.
  If you override CMD, prepend the same.
