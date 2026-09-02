import uuid
import asyncio
from typing import Union
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import get_db
from src.schemas.generation import GenerateRequest, GenerateResponse, GenerationRequestResponse, SourceCitation
from src.services.generation import generate_content
from src.services.streaming import stream_generation_content
from src.repositories import generation_repo
from src.api.dependencies import get_current_tenant, get_current_client
from src.models.tenant import Tenant
from src.models.client import Client

router = APIRouter(tags=["Generate"])


@router.post("/generate", response_model=GenerateResponse, status_code=status.HTTP_200_OK)
async def create_generation(
    request: GenerateRequest,
    stream: bool = Query(False),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
) -> Union[GenerateResponse, StreamingResponse]:
    # 1. Fetch the client and validate it belongs to the tenant
    client = await get_current_client(request.client_id, tenant, db)
    
    if stream:
        gen_request = await generation_repo.create_generation_request(
            session=db,
            tenant_id=tenant.id,
            client_id=client.id,
            brief=request.brief
        )
        return StreamingResponse(
            stream_generation_content(db, client, tenant, request.brief, gen_request.id),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
                "Connection": "keep-alive",
                "X-Generation-ID": str(gen_request.id)
            }
        )
    
    # 2. Call generate_content with a timeout
    try:
        # Wrap in wait_for to enforce the 30s timeout requested in Sprint 06
        gen_request = await asyncio.wait_for(
            generate_content(db, client, tenant, request.brief),
            timeout=30.0
        )
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT, 
            detail="Generation timed out after 30 seconds."
        )

    # Convert to GenerateResponse
    return GenerateResponse(
        request_id=gen_request.id,
        draft=gen_request.output or "",
        sources=[SourceCitation(**s) for s in (gen_request.sources_used or []) if isinstance(s, dict)],
        model_used=gen_request.llm_model_used or "",
        status=gen_request.status
    )


from fastapi import BackgroundTasks

async def _run_async_generation_task(
    tenant_id: uuid.UUID,
    client_id: uuid.UUID,
    brief: str,
    gen_request_id: uuid.UUID
):
    """Background worker for asynchronous generation jobs."""
    from src.db.session import async_session_maker
    from src.repositories import generation_repo
    from src.models.client import Client
    from src.models.tenant import Tenant
    
    async with async_session_maker() as session:
        try:
            client = await session.get(Client, client_id)
            tenant = await session.get(Tenant, tenant_id)
            if not client or not tenant:
                await generation_repo.update_generation_request(
                    session=session,
                    request_id=gen_request_id,
                    status="failed",
                    error_message="Client or Tenant not found for async task"
                )
                return

            await generate_content(session, client, tenant, brief)
        except Exception as e:
            await generation_repo.update_generation_request(
                session=session,
                request_id=gen_request_id,
                status="failed",
                error_message=str(e)
            )

@router.post("/generations/async", status_code=status.HTTP_202_ACCEPTED)
async def create_async_generation(
    request: GenerateRequest,
    background_tasks: BackgroundTasks,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Creates an asynchronous generation job and returns immediately with a request_id."""
    client = await get_current_client(request.client_id, tenant, db)
    
    gen_request = await generation_repo.create_generation_request(
        session=db,
        tenant_id=tenant.id,
        client_id=client.id,
        brief=request.brief
    )
    
    background_tasks.add_task(
        _run_async_generation_task,
        tenant_id=tenant.id,
        client_id=client.id,
        brief=request.brief,
        gen_request_id=gen_request.id
    )
    
    return {
        "request_id": gen_request.id,
        "status": "pending",
        "message": "Generation job queued successfully. Poll /generations/{request_id} for status."
    }

@router.get("/generations/{request_id}", response_model=GenerationRequestResponse)
async def get_generation(
    request_id: uuid.UUID,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
) -> GenerationRequestResponse:
    # We must ensure the generation request belongs to a client owned by the tenant.
    # We can fetch the request, then verify the tenant_id directly since it's on the GenerationRequest model.
    gen_request = await db.get(generation_repo.GenerationRequest, request_id)
    if not gen_request or gen_request.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="Generation request not found")

    return GenerationRequestResponse(
        request_id=gen_request.id,
        brief=gen_request.brief,
        draft=gen_request.output or "",
        sources=[SourceCitation(**s) for s in (gen_request.sources_used or []) if isinstance(s, dict)],
        model_used=gen_request.llm_model_used or "",
        status=gen_request.status,
        created_at=gen_request.created_at,
        error_message=gen_request.error_message
    )

