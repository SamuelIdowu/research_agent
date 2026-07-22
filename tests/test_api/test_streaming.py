import pytest
import json
from uuid import uuid4
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import patch, MagicMock

from src.main import app
from src.agent.agent import parse_agent_output
from src.repositories import tenant_repo, client_repo
from src.schemas.client import ClientCreate
from src.models.tenant import Tenant
from src.api.dependencies import get_current_tenant

@pytest.fixture
async def sample_client(async_session: AsyncSession):
    tenant_obj, _ = await tenant_repo.create_tenant(async_session, "Test Tenant")
    client = await client_repo.create_client(async_session, ClientCreate(name="Test Client", usage_cap=50), tenant_obj.id)
    await async_session.commit()
    return client

@pytest.fixture(autouse=True)
def override_tenant(async_session: AsyncSession):
    async def mock_tenant():
        return Tenant(id=uuid4(), name="Test Tenant")
    app.dependency_overrides[get_current_tenant] = mock_tenant
    yield
    app.dependency_overrides.clear()

def test_parse_agent_output_valid():
    raw_output = "<DRAFT>\nThis is a draft.\n</DRAFT>\n<SOURCES>\n[{\"type\": \"kb\", \"document_id\": \"123\", \"excerpt\": \"test\"}]\n</SOURCES>"
    draft, sources = parse_agent_output(raw_output)
    assert draft == "This is a draft."
    assert len(sources) == 1
    assert sources[0]["document_id"] == "123"

def test_parse_agent_output_malformed():
    raw_output = "<DRAFT>\nThis is a draft.\n</DRAFT>"
    with pytest.raises(ValueError, match="Output missing required"):
        parse_agent_output(raw_output)

@pytest.mark.asyncio
@patch("src.services.generation.run_generation")
async def test_non_streaming_still_works(
    mock_run_generation,
    async_client: AsyncClient,
    sample_client,
    async_session: AsyncSession
):
    tenant = await async_session.get(Tenant, sample_client.tenant_id)
    app.dependency_overrides[get_current_tenant] = lambda: tenant
    
    mock_run_generation.return_value = ("Draft content here.", [{"type": "kb", "excerpt": "Test"}], 100, 50)
    
    response = await async_client.post(
        "/generate",
        json={"brief": "Test brief", "client_id": str(sample_client.id)}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["draft"] == "Draft content here."

@pytest.mark.asyncio
@patch("src.api.routers.generate.stream_generation_content")
async def test_streaming_response_has_correct_content_type(
    mock_stream,
    async_client: AsyncClient,
    sample_client,
    async_session: AsyncSession
):
    tenant = await async_session.get(Tenant, sample_client.tenant_id)
    app.dependency_overrides[get_current_tenant] = lambda: tenant

    async def mock_generator(*args, **kwargs):
        yield '0:"hello"\\n'
        yield 'd:{"finishReason":"stop"}\\n'
        yield '8:[{"type":"kb"}]\\n'
    
    mock_stream.side_effect = mock_generator

    response = await async_client.post(
        "/generate?stream=true",
        json={"brief": "Test brief", "client_id": str(sample_client.id)}
    )
    
    assert response.status_code == 200
    # httpx doesn't perfectly preserve the charset in headers property sometimes or appends it, so we check using in
    assert "text/event-stream" in response.headers.get("Content-Type", "")

@pytest.mark.asyncio
@patch("src.api.routers.generate.stream_generation_content")
async def test_streaming_response_contains_text_chunks(
    mock_stream,
    async_client: AsyncClient,
    sample_client,
    async_session: AsyncSession
):
    tenant = await async_session.get(Tenant, sample_client.tenant_id)
    app.dependency_overrides[get_current_tenant] = lambda: tenant

    async def mock_generator(*args, **kwargs):
        yield '0:"test chunk"\\n'
        
    mock_stream.side_effect = mock_generator

    response = await async_client.post(
        "/generate?stream=true",
        json={"brief": "Test brief", "client_id": str(sample_client.id)}
    )
    
    content = response.content.decode("utf-8")
    assert '0:"test chunk"' in content

@pytest.mark.asyncio
@patch("src.api.routers.generate.stream_generation_content")
async def test_streaming_response_ends_with_done(
    mock_stream,
    async_client: AsyncClient,
    sample_client,
    async_session: AsyncSession
):
    tenant = await async_session.get(Tenant, sample_client.tenant_id)
    app.dependency_overrides[get_current_tenant] = lambda: tenant

    async def mock_generator(*args, **kwargs):
        yield '0:"hello"\\n'
        yield 'd:{"finishReason":"stop"}\\n'
        
    mock_stream.side_effect = mock_generator

    response = await async_client.post(
        "/generate?stream=true",
        json={"brief": "Test brief", "client_id": str(sample_client.id)}
    )
    
    content = response.content.decode("utf-8")
    lines = [line for line in content.split("\\n") if line.strip()]
    assert 'd:{"finishReason":"stop"}' in lines

@pytest.mark.asyncio
@patch("src.api.routers.generate.stream_generation_content")
async def test_streaming_sources_event_present(
    mock_stream,
    async_client: AsyncClient,
    sample_client,
    async_session: AsyncSession
):
    tenant = await async_session.get(Tenant, sample_client.tenant_id)
    app.dependency_overrides[get_current_tenant] = lambda: tenant

    async def mock_generator(*args, **kwargs):
        yield '8:[{"type":"kb"}]\\n'
        
    mock_stream.side_effect = mock_generator

    response = await async_client.post(
        "/generate?stream=true",
        json={"brief": "Test brief", "client_id": str(sample_client.id)}
    )
    
    content = response.content.decode("utf-8")
    assert '8:[{"type":"kb"}]' in content
