import uuid
from fastapi import Request, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.db.session import get_db
from src.models.tenant import Tenant
from src.models.client import Client
from src.api.middleware.auth import authenticate_and_rate_limit

async def get_current_tenant(request: Request, session: AsyncSession = Depends(get_db)) -> Tenant:
    return await authenticate_and_rate_limit(request, session)

async def get_current_client(
    client_id: uuid.UUID, 
    tenant: Tenant = Depends(get_current_tenant), 
    session: AsyncSession = Depends(get_db)
) -> Client:
    stmt = select(Client).where(Client.id == client_id, Client.tenant_id == tenant.id)
    result = await session.execute(stmt)
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return client
