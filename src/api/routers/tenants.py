import uuid
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import get_db
from src.schemas.common import PaginatedResponse
from src.schemas.tenant import TenantCreate, TenantResponse, TenantCreateResponse
from src.repositories import tenant_repo

public_router = APIRouter(tags=["Tenants"])
router = APIRouter(tags=["Tenants"])

@public_router.post("", response_model=TenantCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_tenant(tenant_in: TenantCreate, db: AsyncSession = Depends(get_db)) -> TenantCreateResponse:
    if not tenant_in.name.strip():
        raise HTTPException(status_code=400, detail="Name cannot be empty")
    
    try:
        tenant, raw_key = await tenant_repo.create_tenant(db, tenant_in.name)
        await db.commit()
    except Exception as e:
        await db.rollback()
        # This is a naive catch for IntegrityError, ideally handle duplicate name specifically
        if "unique constraint" in str(e).lower() or "duplicate key" in str(e).lower():
            raise HTTPException(status_code=409, detail="Tenant with this name already exists")
        raise
    
    # We must construct the response to include the raw api key
    tenant_dict = TenantResponse.model_validate(tenant).model_dump()
    tenant_dict["raw_api_key"] = raw_key
    return TenantCreateResponse(**tenant_dict)

@router.get("", response_model=PaginatedResponse[TenantResponse])
async def list_tenants(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    db: AsyncSession = Depends(get_db)
) -> PaginatedResponse[TenantResponse]:
    items, total = await tenant_repo.list_tenants(db, page, page_size)
    return PaginatedResponse(
        items=[TenantResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size
    )

@router.get("/{tenant_id}", response_model=TenantResponse)
async def get_tenant(tenant_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> TenantResponse:
    tenant = await tenant_repo.get_tenant_by_id(db, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return TenantResponse.model_validate(tenant)

@router.delete("/{tenant_id}", response_model=TenantResponse)
async def deactivate_tenant(tenant_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> TenantResponse:
    tenant = await tenant_repo.deactivate_tenant(db, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    await db.commit()
    return TenantResponse.model_validate(tenant)
