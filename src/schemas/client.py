import uuid
from typing import Optional
from pydantic import BaseModel, ConfigDict
from .common import UUIDModel, TimestampedModel

class ClientCreate(BaseModel):
    """Schema for creating a new client."""
    tenant_id: uuid.UUID
    name: str
    usage_cap: Optional[int] = None

class ClientUpdate(BaseModel):
    """Schema for updating an existing client."""
    name: Optional[str] = None
    usage_cap: Optional[int] = None
    is_active: Optional[bool] = None

class ClientResponse(UUIDModel, TimestampedModel):
    """Schema for a client response."""
    tenant_id: uuid.UUID
    name: str
    llm_provider: Optional[str] = None
    llm_model: Optional[str] = None
    usage_cap: Optional[int] = None
    usage_this_month: int
    is_active: bool

    model_config = ConfigDict(from_attributes=True)
