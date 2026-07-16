import uuid
from typing import Tuple, List, Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.tenant import Tenant
from src.schemas.tenant import TenantCreate

from src.repositories.api_key_repo import create_api_key

async def create_tenant(session: AsyncSession, name: str) -> Tuple[Tenant, str]:
    """Creates a new tenant and an initial API key, returns both."""
    tenant = Tenant(
        name=name,
    )
    session.add(tenant)
    await session.flush()
    await session.refresh(tenant)

    # Create initial API key
    _, raw_api_key = await create_api_key(session, tenant.id, "default")

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


