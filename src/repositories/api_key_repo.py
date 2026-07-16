import uuid
from typing import Optional, List, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.api_key import ApiKey
from src.core.security import generate_api_key

async def create_api_key(session: AsyncSession, tenant_id: uuid.UUID, label: str | None = None) -> Tuple[ApiKey, str]:
    """Generates and stores a new API key for a tenant."""
    raw_key, hashed_key = generate_api_key()
    
    api_key = ApiKey(
        tenant_id=tenant_id,
        key_hash=hashed_key,
        label=label,
        is_active=True
    )
    session.add(api_key)
    await session.flush()
    await session.refresh(api_key)
    
    return api_key, raw_key

async def get_by_hash(session: AsyncSession, key_hash: str) -> Optional[ApiKey]:
    """Retrieves an API key by its hash."""
    stmt = select(ApiKey).where(ApiKey.key_hash == key_hash)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()

async def list_for_tenant(session: AsyncSession, tenant_id: uuid.UUID) -> List[ApiKey]:
    """Lists all API keys for a given tenant."""
    stmt = select(ApiKey).where(ApiKey.tenant_id == tenant_id).order_by(ApiKey.created_at.desc())
    result = await session.execute(stmt)
    return list(result.scalars().all())

async def revoke(session: AsyncSession, api_key_id: uuid.UUID, tenant_id: uuid.UUID) -> Optional[ApiKey]:
    """Soft-deletes (revokes) an API key."""
    stmt = select(ApiKey).where(ApiKey.id == api_key_id, ApiKey.tenant_id == tenant_id)
    result = await session.execute(stmt)
    api_key = result.scalar_one_or_none()
    
    if api_key:
        api_key.is_active = False
        await session.flush()
        await session.refresh(api_key)
        
    return api_key
