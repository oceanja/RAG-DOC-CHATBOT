"""Persist and read back chat Q&A for the dashboard's Recent Questions view."""

import logging
import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models import Chunk, Document, Question

log = logging.getLogger(__name__)


@dataclass
class CitationRef:
    chunk_id: uuid.UUID
    title: str | None
    url: str | None


@dataclass
class QuestionRecord:
    id: uuid.UUID
    question_text: str
    answer_text: str
    citations: list[CitationRef]
    created_at: object


async def record_question(
    project_id: uuid.UUID,
    question_text: str,
    answer_text: str,
    cited_chunk_ids: list[uuid.UUID],
    visitor_ip_hash: str | None,
) -> None:
    """Insert a question row in its own session (called after the chat stream)."""
    try:
        async with AsyncSessionLocal() as session:
            session.add(
                Question(
                    project_id=project_id,
                    question_text=question_text,
                    answer_text=answer_text,
                    cited_chunk_ids=cited_chunk_ids,
                    visitor_ip_hash=visitor_ip_hash,
                )
            )
            await session.commit()
    except Exception:
        log.exception("failed to record question for project=%s", project_id)


async def list_questions(
    session: AsyncSession,
    project_id: uuid.UUID,
    limit: int = 100,
) -> list[QuestionRecord]:
    result = await session.execute(
        select(Question)
        .where(Question.project_id == project_id)
        .order_by(Question.created_at.desc())
        .limit(limit)
    )
    questions = list(result.scalars().all())

    # Hydrate citation metadata in one query across all cited chunks.
    all_ids: set[uuid.UUID] = set()
    for q in questions:
        all_ids.update(q.cited_chunk_ids or [])

    meta: dict[uuid.UUID, tuple[str | None, str | None]] = {}
    if all_ids:
        rows = await session.execute(
            select(Chunk.id, Document.title, Document.source_url)
            .join(Document, Chunk.document_id == Document.id)
            .where(Chunk.id.in_(all_ids))
        )
        for chunk_id, title, url in rows.all():
            meta[chunk_id] = (title, url)

    records: list[QuestionRecord] = []
    for q in questions:
        citations = [
            CitationRef(
                chunk_id=cid,
                title=meta.get(cid, (None, None))[0],
                url=meta.get(cid, (None, None))[1],
            )
            for cid in (q.cited_chunk_ids or [])
        ]
        records.append(
            QuestionRecord(
                id=q.id,
                question_text=q.question_text,
                answer_text=q.answer_text,
                citations=citations,
                created_at=q.created_at,
            )
        )
    return records
