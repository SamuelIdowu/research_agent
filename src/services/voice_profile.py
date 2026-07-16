import uuid
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.voice_profile import VoiceProfile
from src.repositories import voice_profile_repo

async def get_voice_profile_prompt_fragment(db: AsyncSession, client_id: uuid.UUID) -> str:
    """Builds the voice profile prompt block for LLM injection."""
    profile = await voice_profile_repo.get_voice_profile(db, client_id)
    if not profile:
        return ""

    lines = ["## Voice Profile"]
    if profile.tone:
        lines.append(f"- Tone: {profile.tone}")
    if profile.pov:
        lines.append(f"- Point of View: {profile.pov}")
    if profile.banned_words:
        lines.append(f"- Banned Words/Phrases: {', '.join(profile.banned_words)}")
    if profile.extra_instructions:
        lines.append(f"- Additional Instructions: {profile.extra_instructions}")
        
    if len(lines) == 1:
        # If no fields are actually set
        return ""

    return "\n".join(lines)

async def validate_voice_profile_constraints(profile: VoiceProfile, draft: str) -> list[str]:
    """Checks if banned words appear in the draft text (case-insensitive)."""
    if not profile or not profile.banned_words:
        return []
        
    violations = []
    draft_lower = draft.lower()
    
    for word in profile.banned_words:
        if word.lower() in draft_lower:
            violations.append(word)
            
    return violations
