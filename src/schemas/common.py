from datetime import datetime
from typing import Generic, TypeVar, Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")

class UUIDModel(BaseModel):
    """Base model with a UUID."""
    id: uuid.UUID

    model_config = ConfigDict(from_attributes=True)

class TimestampedModel(BaseModel):
    """Base model with timestamps."""
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response model."""
    items: list[T]
    total: int
    page: int
    page_size: int
