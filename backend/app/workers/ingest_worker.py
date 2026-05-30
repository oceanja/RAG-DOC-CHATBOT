"""ARQ worker that runs ingestion jobs out-of-band from HTTP requests.

Run with:  arq app.workers.ingest_worker.WorkerSettings
"""

import logging
import uuid
from typing import Any

from arq.connections import RedisSettings

from app.config import settings
from app.database import AsyncSessionLocal
from app.models import Project
from app.services.ingestion import ingest_markdown, ingest_url
from app.startup import init_db

log = logging.getLogger(__name__)


async def ingest_markdown_job(
    ctx: dict[str, Any],
    project_id: str,
    raw_md: str,
    default_title: str = "Untitled",
) -> dict[str, int]:
    """Worker entrypoint for markdown ingestion."""
    async with AsyncSessionLocal() as session:
        project = await session.get(Project, uuid.UUID(project_id))
        if project is None:
            raise RuntimeError(f"Project {project_id} not found")
        result = await ingest_markdown(
            session, project, raw_md, default_title=default_title
        )
        return {
            "document_count": result.document_count,
            "chunk_count": result.chunk_count,
        }


async def ingest_url_job(
    ctx: dict[str, Any],
    project_id: str,
    url: str,
    max_pages: int = 200,
) -> dict[str, int]:
    """Worker entrypoint for sitemap-based URL ingestion."""
    async with AsyncSessionLocal() as session:
        project = await session.get(Project, uuid.UUID(project_id))
        if project is None:
            raise RuntimeError(f"Project {project_id} not found")
        result = await ingest_url(session, project, url, max_pages=max_pages)
        return {
            "document_count": result.document_count,
            "chunk_count": result.chunk_count,
        }


async def on_startup(ctx: dict[str, Any]) -> None:
    await init_db()
    log.info("ARQ worker ready (redis=%s)", settings.redis_url)


class WorkerSettings:
    functions = [ingest_markdown_job, ingest_url_job]
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    on_startup = on_startup
    max_tries = 1  # retries handled per-batch inside embed_batch
    job_timeout = 60 * 30
