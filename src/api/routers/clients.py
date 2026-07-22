import uuid
from typing import Annotated, List, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import get_db
from src.schemas.common import PaginatedResponse
from src.schemas.client import ClientCreate, ClientUpdate, ClientResponse
from src.schemas.document import DocumentResponse
from src.repositories import client_repo
from src.repositories import tenant_repo
from src.api.dependencies import get_current_tenant
from src.models.tenant import Tenant

router = APIRouter(tags=["Clients"])

@router.post("", response_model=ClientResponse, status_code=status.HTTP_201_CREATED)
async def create_client(
    client_in: ClientCreate, 
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
) -> ClientResponse:
    try:
        client = await client_repo.create_client(db, client_in, tenant.id)
        await db.commit()
        return ClientResponse.model_validate(client)
    except Exception as e:
        await db.rollback()
        raise

@router.get("", response_model=PaginatedResponse[ClientResponse])
async def list_clients(
    tenant: Tenant = Depends(get_current_tenant),
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    db: AsyncSession = Depends(get_db)
) -> PaginatedResponse[ClientResponse]:
    items, total = await client_repo.list_clients(db, tenant.id, page, page_size)
    return PaginatedResponse(
        items=[ClientResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size
    )

@router.get("/{client_id}", response_model=ClientResponse)
async def get_client(
    client_id: uuid.UUID, 
    tenant: Tenant = Depends(get_current_tenant), 
    db: AsyncSession = Depends(get_db)
) -> ClientResponse:
    client = await client_repo.get_client_by_id(db, client_id, tenant.id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return ClientResponse.model_validate(client)

@router.patch("/{client_id}", response_model=ClientResponse)
async def update_client(
    client_id: uuid.UUID, 
    client_in: ClientUpdate, 
    tenant: Tenant = Depends(get_current_tenant), 
    db: AsyncSession = Depends(get_db)
) -> ClientResponse:
    client = await client_repo.update_client(db, client_id, tenant.id, client_in)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    await db.commit()
    return ClientResponse.model_validate(client)

@router.delete("/{client_id}", response_model=ClientResponse)
async def deactivate_client(
    client_id: uuid.UUID, 
    tenant: Tenant = Depends(get_current_tenant), 
    db: AsyncSession = Depends(get_db)
) -> ClientResponse:
    client = await client_repo.deactivate_client(db, client_id, tenant.id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    await db.commit()
    return ClientResponse.model_validate(client)

@router.get("/{client_id}/documents", response_model=PaginatedResponse[DocumentResponse])
async def list_client_documents(
    client_id: uuid.UUID, 
    tenant: Tenant = Depends(get_current_tenant), 
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    db: AsyncSession = Depends(get_db)
) -> PaginatedResponse[DocumentResponse]:
    from src.repositories import document_repo
    items, total = await document_repo.list_documents(db, client_id, tenant.id, page, page_size)
    return PaginatedResponse(
        items=[DocumentResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size
    )

from src.schemas.generation import GenerationRequestResponse, SourceCitation

@router.get("/{client_id}/generations", response_model=PaginatedResponse[GenerationRequestResponse])
async def list_client_generations(
    client_id: uuid.UUID, 
    tenant: Tenant = Depends(get_current_tenant), 
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    db: AsyncSession = Depends(get_db)
) -> PaginatedResponse[GenerationRequestResponse]:
    from src.repositories import generation_repo
    
    # First verify client belongs to tenant (implicit check from get_client_by_id)
    client = await client_repo.get_client_by_id(db, client_id, tenant.id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    items, total = await generation_repo.list_generation_requests(db, client_id, page, page_size)
    return PaginatedResponse(
        items=[
            GenerationRequestResponse(
                request_id=i.id,
                brief=i.brief,
                draft=i.output or "",
                sources=[SourceCitation(**s) for s in (i.sources_used or []) if isinstance(s, dict)],
                model_used=i.llm_model_used or "",
                status=i.status,
                created_at=i.created_at,
                error_message=i.error_message
            ) for i in items
        ],
        total=total,
        page=page,
        page_size=page_size
    )
