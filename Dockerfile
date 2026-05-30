# syntax=docker/dockerfile:1.7

# ---- Stage 1: build the embed widget bundle ----
FROM node:20-alpine AS widget-build
WORKDIR /widget
COPY widget/package.json widget/package-lock.json* ./
RUN npm install --no-audit --no-fund
COPY widget/ ./
RUN npm run build

# ---- Stage 2: backend runtime ----
FROM python:3.11-slim AS backend
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    AUTO_CREATE_TABLES=false \
    WIDGET_BUNDLE_PATH=/srv/widget/dist/widget.js

RUN apt-get update \
 && apt-get install -y --no-install-recommends curl \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /srv/backend
COPY backend/pyproject.toml ./
RUN pip install --no-cache-dir .

COPY backend/ ./
COPY --from=widget-build /widget/dist /srv/widget/dist

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s \
  CMD curl -fs http://localhost:${PORT:-8000}/health || exit 1

# Default: web. Override CMD for the worker service:
#   CMD ["arq", "app.workers.ingest_worker.WorkerSettings"]
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
