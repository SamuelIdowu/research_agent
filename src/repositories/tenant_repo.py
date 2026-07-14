import secrets
import uuid
import bcrypt
from typing import Tuple, List, Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.tenant import Tenant
from src.schemas.tenant import TenantCreate

async def create_tenant(session: AsyncSession, name: str) -> Tuple[Tenant, str]:
    """Creates a new tenant and returns the tenant object along with the raw API key."""
    raw_api_key = secrets.token_urlsafe(32)
    # Hash the API key using bcrypt directly
    api_key_bytes = raw_api_key.encode('utf-8')
    salt = bcrypt.gensalt()
    api_key_hash = bcrypt.hashpw(api_key_bytes, salt).decode('utf-8')

    tenant = Tenant(
        name=name,
        api_key_hash=api_key_hash
    )
    session.add(tenant)
    await session.flush()
    await session.refresh(tenant)

    return tenant, raw_api_key

async def get_tenant_by_id(session: AsyncSession, tenant_id: uuid.UUID) -> Optional[Tenant]:
    """Retrieve a tenant by ID."""
    stmt = select(Tenant).where(Tenant.id == tenant_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()

async def list_tenants(session: AsyncSession, page: int, page_size: int) -> Tuple[List[Tenant], int]:
    """List tenants with pagination."""
    # Count total
    count_stmt = select(func.count(Tenant.id))
    total_result = await session.execute(count_stmt)
    total = total_result.scalar_one()

    # Get items
    offset = (page - 1) * page_size
    stmt = select(Tenant).offset(offset).limit(page_size).order_by(Tenant.created_at.desc())
    result = await session.execute(stmt)
    items = list(result.scalars().all())

    return items, total

async def deactivate_tenant(session: AsyncSession, tenant_id: uuid.UUID) -> Optional[Tenant]:
    """Soft delete a tenant by setting is_active to False."""
    tenant = await get_tenant_by_id(session, tenant_id)
    if tenant:
        tenant.is_active = False
        await session.flush()
        await session.refresh(tenant)
    return tenant

async def get_tenant_by_api_key_hash(session: AsyncSession, key_hash: str) -> Optional[Tenant]:
    """Retrieve a tenant by their API key hash."""
    stmt = select(Tenant).where(Tenant.api_key_hash == key_hash, Tenant.is_active == True)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()
