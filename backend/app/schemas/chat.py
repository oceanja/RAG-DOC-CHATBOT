from uuid import UUID

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    project_id: UUID
    question: str = Field(..., min_length=1, max_length=2000)


class CitationOut(BaseModel):
    chunk_id: UUID
    document_id: UUID
    title: str
    url: str | None
    snippet: str


class ChatResponse(BaseModel):
    answer: str
    citations: list[CitationOut]
