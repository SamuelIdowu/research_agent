from datetime import datetime
from typing import Literal, Optional
from uuid import UUID
from pydantic import BaseModel, Field


class GenerateRequest(BaseModel):
    brief: str = Field(..., min_length=1, max_length=5000)
    client_id: UUID

    model_config = {
        "json_schema_extra": {
            "example": {
                "brief": "Write a short blog post about AI agents.",
                "client_id": "123e4567-e89b-12d3-a456-426614174000"
            }
        }
    }


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
