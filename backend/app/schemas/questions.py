from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class CitationRefOut(BaseModel):
    chunk_id: UUID
    title: str | None
    url: str | None


class QuestionOut(BaseModel):
    id: UUID
    question_text: str
    answer_text: str
    citations: list[CitationRefOut]
    created_at: datetime
