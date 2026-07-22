import uuid

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import get_db
from src.schemas.common import PaginatedResponse
from src.schemas.document import DocumentIngestRequest, DocumentResponse
from src.repositories import document_repo
from src.services.ingestion import ingest_document
from src.models.tenant import Tenant
from src.api.dependencies import get_current_tenant, get_current_client

from typing import Annotated

router = APIRouter(tags=["Documents"])

@router.get("", response_model=PaginatedResponse[DocumentResponse])
async def list_documents(
    client_id: uuid.UUID = Query(..., description="The client that owns the documents"),
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    client = await get_current_client(client_id, tenant, db)
    items, total = await document_repo.list_documents(db, client.id, tenant.id, page, page_size)
    return PaginatedResponse(
        items=[DocumentResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size
    )

@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def create_document(
    request: DocumentIngestRequest,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    # Resolve client from request payload, verifying it belongs to the authenticated tenant
    client = await get_current_client(request.client_id, tenant, db)
    try:
        # Create document row
        document = await document_repo.create_document(
            session=db,
            client_id=client.id,
            tenant_id=client.tenant_id,
            source_type=request.source_type,
            title=request.title,
            source_url=str(request.url) if request.url and request.source_type == "url" else None
        )
        
        # Synchronous ingestion (blocking until complete as requested for v1)
        await ingest_document(
            session=db,
            document_id=document.id,
            client_id=client.id,
            source_type=request.source_type,
            content=request.content,
            url=str(request.url) if request.url else None
        )
        
        # Refresh document to get updated status
        updated_doc = await document_repo.get_document(db, document.id, client.id)
        if not updated_doc:
            raise HTTPException(status_code=404, detail="Document not found")
        return DocumentResponse.model_validate(updated_doc)
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: uuid.UUID,
    client_id: uuid.UUID = Query(..., description="The client that owns the document"),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    client = await get_current_client(client_id, tenant, db)
    document = await document_repo.get_document(db, document_id, client.id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return DocumentResponse.model_validate(document)

@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: uuid.UUID,
    client_id: uuid.UUID = Query(..., description="The client that owns the document"),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    client = await get_current_client(client_id, tenant, db)
    success = await document_repo.delete_document(db, document_id, client.id)
    if not success:
        raise HTTPException(status_code=404, detail="Document not found")
    return None
