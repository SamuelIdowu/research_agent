from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, model_validator


class DocumentIngestRequest(BaseModel):
    source_type: Literal["text", "url"]
    title: Optional[str] = None
    content: Optional[str] = None
    url: Optional[str] = None

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
