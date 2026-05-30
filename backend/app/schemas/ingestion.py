from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class IngestRequest(BaseModel):
    type: Literal["markdown", "url"]
    content: str | None = Field(
        None, description="Raw markdown body (required when type=markdown)"
    )
    url: str | None = Field(
        None, description="Base URL of the docs site (required when type=url)"
    )
    default_title: str = "Untitled"
    max_pages: int = Field(200, ge=1, le=1000)

    @model_validator(mode="after")
    def _require_field_for_type(self) -> "IngestRequest":
        if self.type == "markdown" and not (self.content and self.content.strip()):
            raise ValueError("`content` is required when type=markdown")
        if self.type == "url" and not (self.url and self.url.strip()):
            raise ValueError("`url` is required when type=url")
        return self


class IngestEnqueuedResponse(BaseModel):
    project_id: UUID
    job_id: str
    status: str
    type: str
