import uuid
from typing import Tuple, List, Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.client import Client
from src.schemas.client import ClientCreate, ClientUpdate

async def create_client(session: AsyncSession, data: ClientCreate) -> Client:
    """Creates a new client for a specific tenant."""
    client = Client(
        tenant_id=data.tenant_id,
        name=data.name,
        usage_cap=data.usage_cap
    )
    session.add(client)
    await session.flush()
    await session.refresh(client)
    return client

async def get_client_by_id(session: AsyncSession, client_id: uuid.UUID, tenant_id: uuid.UUID) -> Optional[Client]:
    """Retrieve a client by ID, scoped to a tenant."""
    stmt = select(Client).where(Client.id == client_id, Client.tenant_id == tenant_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()

async def list_clients(session: AsyncSession, tenant_id: uuid.UUID, page: int, page_size: int) -> Tuple[List[Client], int]:
    """List clients scoped to a tenant, with pagination."""
    # Count total
    count_stmt = select(func.count(Client.id)).where(Client.tenant_id == tenant_id)
    total_result = await session.execute(count_stmt)
    total = total_result.scalar_one()

    # Get items
    offset = (page - 1) * page_size
    stmt = select(Client).where(Client.tenant_id == tenant_id).offset(offset).limit(page_size).order_by(Client.created_at.desc())
    result = await session.execute(stmt)
    items = list(result.scalars().all())

    return items, total

async def update_client(session: AsyncSession, client_id: uuid.UUID, tenant_id: uuid.UUID, data: ClientUpdate) -> Optional[Client]:
    """Update specific fields of a client."""
    client = await get_client_by_id(session, client_id, tenant_id)
    if client:
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(client, key, value)
        await session.flush()
        await session.refresh(client)
    return client

async def deactivate_client(session: AsyncSession, client_id: uuid.UUID, tenant_id: uuid.UUID) -> Optional[Client]:
    """Soft delete a client by setting is_active to False."""
    client = await get_client_by_id(session, client_id, tenant_id)
    if client:
        client.is_active = False
        await session.flush()
        await session.refresh(client)
    return client
