import uuid
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
from .common import UUIDModel, TimestampedModel

class ClientCreate(BaseModel):
    """Schema for creating a new client."""
    id: Optional[uuid.UUID] = None
    name: str = Field(..., max_length=255)
    usage_cap: Optional[int] = Field(None, gt=0, le=10000)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Marketing Team",
                "usage_cap": 1000
            }
        }
    )

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

class BYOKConfigRequest(BaseModel):
    """Schema for configuring a client's BYOK settings."""
    llm_provider: str
    llm_model: str
    llm_api_key: str

class BYOKConfigResponse(BaseModel):
    """Schema for returning BYOK configuration status. Never returns the API key."""
    llm_provider: str
    llm_model: str
    byok_configured: bool
