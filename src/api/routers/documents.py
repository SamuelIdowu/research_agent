import uuid

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import get_db
from src.schemas.document import DocumentIngestRequest, DocumentResponse
from src.repositories import document_repo
from src.services.ingestion import ingest_document
from src.models.client import Client
from src.api.dependencies import get_current_client

router = APIRouter(tags=["Documents"])

@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def create_document(
    request: DocumentIngestRequest,
    client: Client = Depends(get_current_client),
    db: AsyncSession = Depends(get_db)
):
    try:
        # Create document row
        document = await document_repo.create_document(
            session=db,
            client_id=client.id,
            tenant_id=client.tenant_id,
            source_type=request.source_type,
            title=request.title,
            source_url=request.url if request.source_type == "url" else None
        )
        
        # Synchronous ingestion (blocking until complete as requested for v1)
        await ingest_document(
            session=db,
            document_id=document.id,
            client_id=client.id,
            source_type=request.source_type,
            content=request.content,
            url=request.url
        )
        
        # Refresh document to get updated status
        updated_doc = await document_repo.get_document(db, document.id, client.id)
        if not updated_doc:
            raise HTTPException(status_code=404, detail="Document not found")
        return DocumentResponse.model_validate(updated_doc)
        
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: uuid.UUID,
    client: Client = Depends(get_current_client),
    db: AsyncSession = Depends(get_db)
):
    document = await document_repo.get_document(db, document_id, client.id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return DocumentResponse.model_validate(document)

@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: uuid.UUID,
    client: Client = Depends(get_current_client),
    db: AsyncSession = Depends(get_db)
):
    success = await document_repo.delete_document(db, document_id, client.id)
    if not success:
        raise HTTPException(status_code=404, detail="Document not found")
    return None
