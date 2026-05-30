"""Top-K vector search over a project's chunks using pgvector cosine distance."""

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import Chunk, Document


@dataclass
class RetrievedChunk:
    chunk_id: UUID
    document_id: UUID
    title: str
    source_url: str | None
    content: str
    distance: float


async def retrieve_top_k(
    session: AsyncSession,
    project_id: UUID,
    query_embedding: list[float],
    k: int | None = None,
) -> list[RetrievedChunk]:
    k = k or settings.retrieval_top_k
    distance = Chunk.embedding.cosine_distance(query_embedding).label("distance")

    stmt = (
        select(Chunk, Document, distance)
        .join(Document, Chunk.document_id == Document.id)
        .where(Chunk.project_id == project_id)
        .where(Chunk.embedding.is_not(None))
        .order_by(distance)
        .limit(k)
    )

    result = await session.execute(stmt)
    return [
        RetrievedChunk(
            chunk_id=chunk.id,
            document_id=document.id,
            title=document.title,
            source_url=document.source_url,
            content=chunk.content,
            distance=float(dist),
        )
        for chunk, document, dist in result.all()
    ]
