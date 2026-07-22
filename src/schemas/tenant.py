from pydantic import BaseModel, ConfigDict, Field
from .common import UUIDModel, TimestampedModel

class TenantCreate(BaseModel):
    """Schema for creating a new tenant."""
    name: str = Field(..., max_length=255, pattern=r"^[a-zA-Z0-9\s]+$")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Acme Corp"
            }
        }
    )

class TenantResponse(UUIDModel, TimestampedModel):
    """Schema for a tenant response, excluding sensitive data like API keys."""
    name: str
    is_active: bool

    model_config = ConfigDict(from_attributes=True)

class TenantCreateResponse(TenantResponse):
    """Schema for a tenant creation response, includes the raw API key."""
    raw_api_key: str
