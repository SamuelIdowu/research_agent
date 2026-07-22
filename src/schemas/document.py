from datetime import datetime
from typing import Literal, Optional
from uuid import UUID
import re

from pydantic import BaseModel, ConfigDict, model_validator, Field, AnyHttpUrl


class DocumentIngestRequest(BaseModel):
    client_id: UUID
    source_type: Literal["text", "url"]
    title: Optional[str] = None
    content: Optional[str] = Field(None, max_length=500000)
    url: Optional[AnyHttpUrl] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "client_id": "123e4567-e89b-12d3-a456-426614174000",
                "source_type": "text",
                "title": "Example Document",
                "content": "This is some example content.",
            }
        }
    )

    @model_validator(mode="after")
    def check_source_content(self) -> "DocumentIngestRequest":
        if self.source_type == "text" and not self.content:
            raise ValueError("content is required when source_type is text")
        if self.source_type == "url" and not self.url:
            raise ValueError("url is required when source_type is url")
        return self


class DocumentResponse(BaseModel):
    id: UUID
    client_id: UUID
    source_type: str
    title: Optional[str] = None
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentChunkResponse(BaseModel):
    id: UUID
    document_id: UUID
    text: str
    chunk_index: int

    model_config = ConfigDict(from_attributes=True)
