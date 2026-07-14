from pydantic import BaseModel, ConfigDict
from .common import UUIDModel, TimestampedModel

class TenantCreate(BaseModel):
    """Schema for creating a new tenant."""
    name: str

class TenantResponse(UUIDModel, TimestampedModel):
    """Schema for a tenant response, excluding sensitive data like API keys."""
    name: str
    is_active: bool

    model_config = ConfigDict(from_attributes=True)

class TenantCreateResponse(TenantResponse):
    """Schema for a tenant creation response, includes the raw API key."""
    raw_api_key: str
