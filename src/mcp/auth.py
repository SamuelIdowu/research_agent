from typing import cast
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.core.security import hash_api_key
from src.models.api_key import ApiKey
from src.models.tenant import Tenant

async def get_mcp_tenant(api_key: str, session: AsyncSession) -> Tenant:
    """Authenticates the API key for MCP tools and returns the Tenant."""
    if not api_key:
        raise PermissionError("Invalid API key")
    
    key_hash = hash_api_key(api_key)
    
    stmt = (
        select(ApiKey, Tenant)
        .join(Tenant)
        .where(ApiKey.key_hash == key_hash)
    )
    result = await session.execute(stmt)
    row = result.first()
    
    if not row:
        raise PermissionError("Invalid API key")
        
    api_key_obj = cast(ApiKey, row[0])
    tenant = cast(Tenant, row[1])
    
    if not api_key_obj.is_active or not tenant.is_active:
        raise PermissionError("Invalid API key or Tenant suspended")
        
    return tenant
