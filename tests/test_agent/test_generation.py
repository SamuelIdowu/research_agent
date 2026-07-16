import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4
from src.agent.tools import AgentDeps
from src.agent.agent import run_generation

@pytest.fixture
def mock_deps():
    return AgentDeps(
        session=AsyncMock(),
        client_id=uuid4(),
        tenant_id=uuid4(),
        voice_profile_fragment="Test Voice",
        tavily_api_key="test"
    )

@pytest.mark.asyncio
@patch("src.agent.agent.agent.run")
async def test_run_generation_basic(mock_agent_run, mock_deps):
    class MockResult:
        data = "<DRAFT>\nTest draft\n</DRAFT>\n<SOURCES>\n[{\"type\": \"kb\", \"document_id\": \"123\", \"excerpt_used\": \"KB source\"}]\n</SOURCES>"
        
    mock_agent_run.return_value = MockResult()
    
    draft, sources = await run_generation(mock_deps, "brief")
    
    assert draft == "Test draft"
    assert len(sources) == 1
    assert sources[0]["type"] == "kb"

@pytest.mark.asyncio
@patch("src.services.generation.run_generation")
@patch("src.repositories.generation_repo.update_generation_request")
@patch("src.repositories.generation_repo.create_generation_request")
@patch("src.repositories.voice_profile_repo.get_voice_profile")
@patch("src.services.voice_profile.get_voice_profile_prompt_fragment")
@patch("src.services.generation.byok.resolve_model_for_client")
async def test_generation_logs_to_db(
    mock_resolve_model, mock_vp_frag, mock_vp, mock_create, mock_update, mock_run
):
    from src.services.generation import generate_content
    from src.models.generation_request import GenerationRequest
    
    class MockClient:
        id = uuid4()
        llm_api_key_encrypted = "mock_key"
        llm_provider = "google"
        usage_count = 0
        usage_reset_date = None
    
    class MockTenant:
        id = uuid4()
        
    mock_vp_frag.return_value = "Tone: professional"
    mock_vp.return_value = None
    mock_resolve_model.return_value = ("gemini-2.0-flash", "fake_key")
    
    gen_id = uuid4()
    mock_create.return_value = GenerationRequest(id=gen_id, status="pending")
    mock_run.return_value = ("Test draft", [])
    mock_update.return_value = GenerationRequest(id=gen_id, status="completed")
    
    result = await generate_content(AsyncMock(), MockClient(), MockTenant(), "brief")
    
    assert result.id == gen_id
    assert result.status == "completed"
    
    mock_create.assert_called_once()
    mock_update.assert_called_once()
