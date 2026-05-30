import json
import logging
import uuid
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import Project
from app.schemas.chat import ChatRequest
from app.security import hash_ip
from app.services.chat import stream_answer
from app.services.questions import record_question

router = APIRouter(prefix="/api", tags=["chat"])
log = logging.getLogger(__name__)

SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",  # disable nginx/proxy buffering
}


def _sse(payload: str) -> str:
    return f"data: {payload}\n\n"


async def _event_stream(
    session: AsyncSession,
    project: Project,
    question: str,
    ip_hash: str | None,
) -> AsyncIterator[str]:
    answer_parts: list[str] = []
    cited_ids: list[uuid.UUID] = []
    errored = False
    try:
        async for event in stream_answer(session, project, question):
            if event["type"] == "token":
                answer_parts.append(event["text"])
            elif event["type"] == "citations":
                cited_ids = [uuid.UUID(item["chunk_id"]) for item in event["items"]]
            yield _sse(json.dumps(event, ensure_ascii=False))
    except Exception as exc:
        errored = True
        log.exception("chat stream failed for project=%s", project.id)
        yield _sse(json.dumps({"type": "error", "message": str(exc)}))
    finally:
        yield _sse("[DONE]")

    if not errored and answer_parts:
        await record_question(
            project_id=project.id,
            question_text=question,
            answer_text="".join(answer_parts),
            cited_chunk_ids=cited_ids,
            visitor_ip_hash=ip_hash,
        )


@router.post("/chat")
async def chat_endpoint(
    body: ChatRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> StreamingResponse:
    project = await session.get(Project, body.project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    ip_hash = hash_ip(request.client.host if request.client else None)

    return StreamingResponse(
        _event_stream(session, project, body.question, ip_hash),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )
