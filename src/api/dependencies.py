import uuid
from fastapi import Request, Depends, HTTPException, Security
from fastapi.security import APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.db.session import get_db
from src.models.tenant import Tenant
from src.models.client import Client
from src.api.middleware.auth import authenticate_and_rate_limit

api_key_scheme = APIKeyHeader(name="X-Api-Key", auto_error=False)

async def get_current_tenant(
    request: Request, 
    api_key: str | None = Security(api_key_scheme),
    session: AsyncSession = Depends(get_db)
) -> Tenant:
    return await authenticate_and_rate_limit(request, session, api_key)

async def get_current_client(
    client_id: uuid.UUID, 
    tenant: Tenant = Depends(get_current_tenant), 
    session: AsyncSession = Depends(get_db)
) -> Client:
    stmt = select(Client).where(Client.id == client_id, Client.tenant_id == tenant.id)
    result = await session.execute(stmt)
    client = result.scalar_one_or_none()
    if not client:
        # Auto-provision client for this tenant on demand so frontend calls never 404
        client = Client(
            id=client_id,
            tenant_id=tenant.id,
            name=f"Client {client_id}",
        )
        session.add(client)
        await session.commit()
        await session.refresh(client)
    return client
