from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_session
from app.dependencies import require_admin
from app.models import Project, ProjectStatus
from app.schemas.ingestion import IngestEnqueuedResponse, IngestRequest
from app.schemas.projects import ProjectCreate, ProjectDetailOut, ProjectOut
from app.schemas.questions import CitationRefOut, QuestionOut
from app.services.questions import list_questions

router = APIRouter(
    prefix="/api/projects",
    tags=["projects"],
    dependencies=[Depends(require_admin)],
)


def _embed_snippet(project_id: UUID) -> str:
    base = settings.public_base_url.rstrip("/")
    return (
        f'<script src="{base}/widget.js" '
        f'data-project-id="{project_id}" '
        f'data-api-base="{base}"></script>'
    )


@router.get("", response_model=list[ProjectOut])
async def list_projects(
    session: AsyncSession = Depends(get_session),
) -> list[Project]:
    result = await session.execute(select(Project).order_by(Project.created_at.desc()))
    return list(result.scalars().all())


@router.post("", response_model=ProjectDetailOut, status_code=status.HTTP_201_CREATED)
async def create_project(
    body: ProjectCreate,
    session: AsyncSession = Depends(get_session),
) -> ProjectDetailOut:
    project = Project(name=body.name, docs_url=body.docs_url)
    session.add(project)
    await session.commit()
    await session.refresh(project)
    return ProjectDetailOut(
        **ProjectOut.model_validate(project).model_dump(),
        embed_snippet=_embed_snippet(project.id),
    )


@router.get("/{project_id}", response_model=ProjectDetailOut)
async def get_project(
    project_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> ProjectDetailOut:
    project = await session.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return ProjectDetailOut(
        **ProjectOut.model_validate(project).model_dump(),
        embed_snippet=_embed_snippet(project.id),
    )


@router.get("/{project_id}/questions", response_model=list[QuestionOut])
async def get_project_questions(
    project_id: UUID,
    limit: int = Query(100, ge=1, le=500),
    session: AsyncSession = Depends(get_session),
) -> list[QuestionOut]:
    project = await session.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    records = await list_questions(session, project_id, limit=limit)
    return [
        QuestionOut(
            id=r.id,
            question_text=r.question_text,
            answer_text=r.answer_text,
            citations=[
                CitationRefOut(chunk_id=c.chunk_id, title=c.title, url=c.url)
                for c in r.citations
            ],
            created_at=r.created_at,
        )
        for r in records
    ]


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> Response:
    project = await session.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    await session.delete(project)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{project_id}/ingest",
    response_model=IngestEnqueuedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def enqueue_ingest(
    project_id: UUID,
    body: IngestRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> IngestEnqueuedResponse:
    project = await session.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    # Move out of "pending" immediately so the dashboard can distinguish
    # "fresh, never ingested" (pending) from "queued for work" (crawling/embedding).
    project.status = (
        ProjectStatus.CRAWLING if body.type == "url" else ProjectStatus.EMBEDDING
    )
    project.error_message = None
    await session.commit()

    redis_pool = request.app.state.redis_pool
    if body.type == "markdown":
        job = await redis_pool.enqueue_job(
            "ingest_markdown_job",
            str(project.id),
            body.content,
            body.default_title,
        )
    else:  # url
        job = await redis_pool.enqueue_job(
            "ingest_url_job",
            str(project.id),
            body.url,
            body.max_pages,
        )

    if job is None:
        raise HTTPException(status_code=503, detail="Failed to enqueue ingestion job")

    return IngestEnqueuedResponse(
        project_id=project.id,
        job_id=job.job_id,
        status=project.status,
        type=body.type,
    )
