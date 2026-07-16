import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.services.voice_profile import get_voice_profile_prompt_fragment, validate_voice_profile_constraints
from src.models.voice_profile import VoiceProfile
import uuid

@pytest.mark.asyncio
@patch("src.repositories.voice_profile_repo.get_voice_profile")
async def test_prompt_fragment_includes_all_fields(mock_get_voice_profile):
    mock_profile = MagicMock(spec=VoiceProfile)
    mock_profile.tone = "professional"
    mock_profile.pov = "first_person"
    mock_profile.banned_words = ["synergy", "leverage"]
    mock_profile.extra_instructions = "Keep it concise."

    mock_get_voice_profile.return_value = mock_profile

    db_session = AsyncMock()
    fragment = await get_voice_profile_prompt_fragment(db_session, uuid.uuid4())

    assert "## Voice Profile" in fragment
    assert "- Tone: professional" in fragment
    assert "- Point of View: first_person" in fragment
    assert "- Banned Words/Phrases: synergy, leverage" in fragment
    assert "- Additional Instructions: Keep it concise." in fragment

@pytest.mark.asyncio
@patch("src.repositories.voice_profile_repo.get_voice_profile")
async def test_prompt_fragment_no_profile(mock_get_voice_profile):
    mock_get_voice_profile.return_value = None

    db_session = AsyncMock()
    fragment = await get_voice_profile_prompt_fragment(db_session, uuid.uuid4())
    assert fragment == ""

@pytest.mark.asyncio
async def test_banned_word_detection_case_insensitive():
    mock_profile = MagicMock(spec=VoiceProfile)
    mock_profile.banned_words = ["SPAM", "ClickBait"]

    draft = "This is a spam email with clickbait."
    violations = await validate_voice_profile_constraints(mock_profile, draft)
    
    assert len(violations) == 2
    assert "SPAM" in violations
    assert "ClickBait" in violations

@pytest.mark.asyncio
async def test_no_violations_clean_draft():
    mock_profile = MagicMock(spec=VoiceProfile)
    mock_profile.banned_words = ["spam", "clickbait"]

    draft = "This is a perfectly clean email."
    violations = await validate_voice_profile_constraints(mock_profile, draft)
    
    assert len(violations) == 0
