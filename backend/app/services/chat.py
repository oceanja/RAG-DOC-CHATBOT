"""RAG prompt assembly + Gemini call. Supports one-shot and SSE streaming."""

from collections.abc import AsyncIterator
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Project
from app.services import llm
from app.services.retrieval import RetrievedChunk, retrieve_top_k

SYSTEM_INSTRUCTIONS = (
    "You are a helpful assistant for the {project_name} documentation.\n"
    "Answer the user's question using ONLY the context snippets below.\n"
    "If the answer is not contained in the context, reply exactly: I don't know.\n"
    "When you do answer, cite the snippets you used inline using their numbers, "
    "e.g. [1], [2]. Do not invent citations."
)


@dataclass
class Citation:
    chunk_id: UUID
    document_id: UUID
    title: str
    url: str | None
    snippet: str


@dataclass
class ChatResult:
    answer: str
    citations: list[Citation]


def _snippet(text: str, max_chars: int = 240) -> str:
    text = " ".join(text.split())
    return text if len(text) <= max_chars else text[: max_chars - 1].rstrip() + "…"


def _build_prompt(project_name: str, question: str, chunks: list[RetrievedChunk]) -> str:
    header = SYSTEM_INSTRUCTIONS.format(project_name=project_name)
    if not chunks:
        context_block = "(no context found)"
    else:
        context_block = "\n\n".join(
            f"[{i + 1}] {c.content}" for i, c in enumerate(chunks)
        )
    return (
        f"{header}\n\n"
        f"Context:\n{context_block}\n\n"
        f"Question: {question}"
    )


async def _retrieve_and_build(
    session: AsyncSession,
    project: Project,
    question: str,
) -> tuple[str, list[Citation]]:
    [query_vec] = await llm.embed_batch([question], task_type="RETRIEVAL_QUERY")
    chunks = await retrieve_top_k(session, project.id, query_vec)
    prompt = _build_prompt(project.name, question, chunks)
    citations = [
        Citation(
            chunk_id=c.chunk_id,
            document_id=c.document_id,
            title=c.title,
            url=c.source_url,
            snippet=_snippet(c.content),
        )
        for c in chunks
    ]
    return prompt, citations


async def answer_question(
    session: AsyncSession,
    project: Project,
    question: str,
) -> ChatResult:
    prompt, citations = await _retrieve_and_build(session, project, question)
    answer = (await llm.chat(prompt)).strip() or "I don't know."
    return ChatResult(answer=answer, citations=citations)


async def stream_answer(
    session: AsyncSession,
    project: Project,
    question: str,
) -> AsyncIterator[dict]:
    """Yield SSE-shaped events: token*, then citations, then done sentinel."""
    prompt, citations = await _retrieve_and_build(session, project, question)

    async for piece in llm.chat_stream(prompt):
        if piece:
            yield {"type": "token", "text": piece}

    yield {
        "type": "citations",
        "items": [
            {
                "chunk_id": str(c.chunk_id),
                "document_id": str(c.document_id),
                "title": c.title,
                "url": c.url,
                "snippet": c.snippet,
            }
            for c in citations
        ],
    }
