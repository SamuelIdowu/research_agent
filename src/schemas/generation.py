from datetime import datetime
from typing import Literal, Optional
from uuid import UUID
from pydantic import BaseModel, Field


class GenerateRequest(BaseModel):
    brief: str = Field(..., min_length=1, max_length=5000)
    client_id: UUID


class SourceCitation(BaseModel):
    type: Literal["kb", "web"]
    excerpt: str
    url: Optional[str] = None
    document_id: Optional[UUID] = None


class GenerateResponse(BaseModel):
    request_id: UUID
    draft: str
    sources: list[SourceCitation]
    model_used: str
    status: str


class GenerationRequestResponse(GenerateResponse):
    brief: str
    created_at: datetime
    error_message: Optional[str] = None
