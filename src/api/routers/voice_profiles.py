import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import get_db
from src.schemas.voice_profile import VoiceProfileSet, VoiceProfileResponse
from src.repositories import voice_profile_repo
from src.repositories import client_repo
from src.api.dependencies import get_current_tenant
from src.models.tenant import Tenant

router = APIRouter(tags=["Voice Profiles"])

async def check_client_ownership(db: AsyncSession, client_id: uuid.UUID, tenant_id: uuid.UUID):
    client = await client_repo.get_client_by_id(db, client_id, tenant_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return client

@router.put("/{client_id}/voice_profile", response_model=VoiceProfileResponse)
@router.put("/{client_id}/voice-profile", response_model=VoiceProfileResponse)
async def set_voice_profile(
    client_id: uuid.UUID,
    profile_in: VoiceProfileSet,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
) -> VoiceProfileResponse:
    await check_client_ownership(db, client_id, tenant.id)
    
    try:
        profile = await voice_profile_repo.upsert_voice_profile(db, client_id, profile_in)
        await db.commit()
        return VoiceProfileResponse.model_validate(profile)
    except Exception:
        await db.rollback()
        raise

@router.get("/{client_id}/voice_profile", response_model=VoiceProfileResponse)
@router.get("/{client_id}/voice-profile", response_model=VoiceProfileResponse)
async def get_voice_profile(
    client_id: uuid.UUID,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
) -> VoiceProfileResponse:
    await check_client_ownership(db, client_id, tenant.id)
    
    profile = await voice_profile_repo.get_voice_profile(db, client_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Voice profile not found")
    
    return VoiceProfileResponse.model_validate(profile)

@router.delete("/{client_id}/voice_profile", status_code=status.HTTP_204_NO_CONTENT)
@router.delete("/{client_id}/voice-profile", status_code=status.HTTP_204_NO_CONTENT)
async def delete_voice_profile(
    client_id: uuid.UUID,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    await check_client_ownership(db, client_id, tenant.id)
    
    deleted = await voice_profile_repo.delete_voice_profile(db, client_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Voice profile not found")
        
    await db.commit()
