import uuid
from typing import Optional

from sqlalchemy import select, delete
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.voice_profile import VoiceProfile
from src.schemas.voice_profile import VoiceProfileSet

async def upsert_voice_profile(
    db: AsyncSession, client_id: uuid.UUID, data: VoiceProfileSet
) -> VoiceProfile:
    """Upserts a voice profile using PostgreSQL ON CONFLICT DO UPDATE."""
    
    values = {
        "client_id": client_id,
        "tone": data.tone,
        "pov": data.pov,
        "banned_words": data.banned_words,
        "extra_instructions": data.extra_instructions
    }
    
    stmt = insert(VoiceProfile).values(**values)
    
    update_dict = {
        c.name: c
        for c in stmt.excluded
        if c.name not in ["id", "client_id", "created_at"]
    }
    
    upsert_stmt = stmt.on_conflict_do_update(
        index_elements=["client_id"],
        set_=update_dict
    ).returning(VoiceProfile)
    
    result = await db.execute(upsert_stmt)
    return result.scalar_one()

async def get_voice_profile(
    db: AsyncSession, client_id: uuid.UUID
) -> Optional[VoiceProfile]:
    """Retrieves the voice profile for a client."""
    stmt = select(VoiceProfile).where(VoiceProfile.client_id == client_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()

async def delete_voice_profile(
    db: AsyncSession, client_id: uuid.UUID
) -> bool:
    """Deletes the voice profile for a client."""
    stmt = delete(VoiceProfile).where(VoiceProfile.client_id == client_id).returning(VoiceProfile.id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none() is not None
