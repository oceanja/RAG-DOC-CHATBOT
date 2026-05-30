from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    docs_url: str | None = None


class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    docs_url: str | None
    status: str
    last_ingested_at: datetime | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime


class ProjectDetailOut(ProjectOut):
    embed_snippet: str
