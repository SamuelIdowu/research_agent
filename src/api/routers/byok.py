from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from src.db.session import get_db
from src.schemas.client import BYOKConfigRequest, BYOKConfigResponse
from src.models.client import Client
from src.api.dependencies import get_current_client
from src.services import byok

router = APIRouter()

@router.put("/{client_id}/byok", response_model=BYOKConfigResponse)
async def configure_byok_route(
    client_id: UUID,
    request: BYOKConfigRequest,
    client: Client = Depends(get_current_client),
    session: AsyncSession = Depends(get_db)
):
    """Configures Bring-Your-Own-Key for the client."""
    try:
        updated_client = byok.configure_byok(
            client=client, 
            provider=request.llm_provider, 
            model=request.llm_model, 
            raw_key=request.llm_api_key
        )
        await session.commit()
        return BYOKConfigResponse(
            llm_provider=updated_client.llm_provider or "",
            llm_model=updated_client.llm_model or "",
            byok_configured=True
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{client_id}/byok", status_code=status.HTTP_204_NO_CONTENT)
async def remove_byok_route(
    client_id: UUID,
    client: Client = Depends(get_current_client),
    session: AsyncSession = Depends(get_db)
):
    """Removes the BYOK configuration and reverts to default."""
    client.llm_provider = None
    client.llm_model = None
    client.llm_api_key_encrypted = None
    await session.commit()
    return None
