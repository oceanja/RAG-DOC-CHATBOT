"""Ingestion pipelines: markdown (uploaded) and url (sitemap-crawled).

Shared path: write Documents → chunk each → batch-embed → write Chunks.
Status transitions happen here; the ARQ worker just invokes these.
"""

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Chunk, Document, Project, ProjectStatus
from app.services.llm import embed_batch
from app.utils.chunking import chunk_text, split_markdown_by_h1
from app.utils.crawling import crawl_docs

log = logging.getLogger(__name__)


class IngestionResult:
    def __init__(self, document_count: int, chunk_count: int) -> None:
        self.document_count = document_count
        self.chunk_count = chunk_count


@dataclass
class _Section:
    title: str
    body: str
    source_url: str | None = None


async def _commit_status(
    session: AsyncSession,
    project: Project,
    status_: str,
    *,
    error_message: str | None = None,
) -> None:
    project.status = status_
    project.error_message = error_message
    await session.commit()


async def _store_sections(
    session: AsyncSession,
    project: Project,
    sections: list[_Section],
) -> IngestionResult:
    """Write Documents + chunked Chunks for a list of (title, body[, url]) sections."""
    if not sections:
        raise ValueError("No content to ingest")

    documents: list[Document] = []
    per_doc_chunks: list[list[str]] = []
    for sec in sections:
        doc = Document(
            project_id=project.id,
            title=sec.title,
            content=sec.body,
            source_url=sec.source_url,
        )
        session.add(doc)
        documents.append(doc)
        per_doc_chunks.append(chunk_text(sec.body))
    await session.flush()

    flat_texts: list[str] = []
    flat_owners: list[tuple[uuid.UUID, int]] = []
    for doc, doc_chunks in zip(documents, per_doc_chunks, strict=True):
        for idx, content in enumerate(doc_chunks):
            flat_texts.append(content)
            flat_owners.append((doc.id, idx))

    if not flat_texts:
        raise ValueError("No chunks were produced from the input")

    log.info(
        "embedding project=%s docs=%d chunks=%d",
        project.id, len(documents), len(flat_texts),
    )
    embeddings = await embed_batch(flat_texts, task_type="RETRIEVAL_DOCUMENT")

    for (document_id, chunk_index), content, vector in zip(
        flat_owners, flat_texts, embeddings, strict=True
    ):
        session.add(
            Chunk(
                project_id=project.id,
                document_id=document_id,
                chunk_index=chunk_index,
                content=content,
                embedding=vector,
            )
        )

    project.status = ProjectStatus.READY
    project.last_ingested_at = datetime.now(timezone.utc)
    await session.commit()

    return IngestionResult(len(documents), len(flat_texts))


async def _reset_documents(session: AsyncSession, project: Project) -> None:
    await session.execute(delete(Document).where(Document.project_id == project.id))


async def _run_ingestion(
    session: AsyncSession,
    project: Project,
    crawl_status: str,
    section_builder,
) -> IngestionResult:
    await _commit_status(session, project, crawl_status)
    try:
        await _reset_documents(session, project)
        sections = await section_builder()
        await _commit_status(session, project, ProjectStatus.EMBEDDING)
        return await _store_sections(session, project, sections)
    except Exception as exc:
        await session.rollback()
        await _commit_status(
            session, project, ProjectStatus.FAILED,
            error_message=f"{exc.__class__.__name__}: {exc}",
        )
        log.exception("ingestion failed for project=%s", project.id)
        raise


async def ingest_markdown(
    session: AsyncSession,
    project: Project,
    raw_md: str,
    default_title: str = "Untitled",
) -> IngestionResult:
    async def build_sections() -> list[_Section]:
        parsed = split_markdown_by_h1(raw_md, default_title=default_title)
        return [_Section(title=t, body=b) for t, b in parsed]

    return await _run_ingestion(
        session, project, ProjectStatus.EMBEDDING, build_sections
    )


async def ingest_url(
    session: AsyncSession,
    project: Project,
    url: str,
    max_pages: int = 200,
) -> IngestionResult:
    async def build_sections() -> list[_Section]:
        pages = await crawl_docs(url, max_pages=max_pages)
        if not pages:
            raise ValueError(f"Crawl of {url} returned no usable pages")
        return [
            _Section(title=p.title, body=p.content, source_url=p.url)
            for p in pages
        ]

    project.docs_url = url
    await session.commit()
    return await _run_ingestion(
        session, project, ProjectStatus.CRAWLING, build_sections
    )
