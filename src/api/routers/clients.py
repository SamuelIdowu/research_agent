import uuid
from typing import Annotated, List, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import get_db
from src.schemas.common import PaginatedResponse
from src.schemas.client import ClientCreate, ClientUpdate, ClientResponse
from src.repositories import client_repo
from src.repositories import tenant_repo

router = APIRouter(tags=["Clients"])

@router.post("", response_model=ClientResponse, status_code=status.HTTP_201_CREATED)
async def create_client(client_in: ClientCreate, db: AsyncSession = Depends(get_db)) -> ClientResponse:
    # Validate tenant exists
    tenant = await tenant_repo.get_tenant_by_id(db, client_in.tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    try:
        client = await client_repo.create_client(db, client_in)
        await db.commit()
        return ClientResponse.model_validate(client)
    except Exception as e:
        await db.rollback()
        raise

@router.get("", response_model=PaginatedResponse[ClientResponse])
async def list_clients(
    tenant_id: uuid.UUID,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    db: AsyncSession = Depends(get_db)
) -> PaginatedResponse[ClientResponse]:
    items, total = await client_repo.list_clients(db, tenant_id, page, page_size)
    return PaginatedResponse(
        items=[ClientResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size
    )

@router.get("/{client_id}", response_model=ClientResponse)
async def get_client(client_id: uuid.UUID, tenant_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> ClientResponse:
    client = await client_repo.get_client_by_id(db, client_id, tenant_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return ClientResponse.model_validate(client)

@router.patch("/{client_id}", response_model=ClientResponse)
async def update_client(
    client_id: uuid.UUID, 
    tenant_id: uuid.UUID, 
    client_in: ClientUpdate, 
    db: AsyncSession = Depends(get_db)
) -> ClientResponse:
    client = await client_repo.update_client(db, client_id, tenant_id, client_in)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    await db.commit()
    return ClientResponse.model_validate(client)

@router.delete("/{client_id}", response_model=ClientResponse)
async def deactivate_client(client_id: uuid.UUID, tenant_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> ClientResponse:
    client = await client_repo.deactivate_client(db, client_id, tenant_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    await db.commit()
    return ClientResponse.model_validate(client)

@router.get("/{client_id}/documents", response_model=List[dict[str, Any]])
async def list_client_documents(client_id: uuid.UUID, tenant_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> List[dict[str, Any]]:
    """Stub: fulfilled in Sprint 04"""
    return []

@router.get("/{client_id}/generations", response_model=List[dict[str, Any]])
async def list_client_generations(client_id: uuid.UUID, tenant_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> List[dict[str, Any]]:
    """Stub: fulfilled in Sprint 06"""
    return []
