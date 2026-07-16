import pytest
import uuid
from sqlalchemy import select
from src.models.client import Client
from src.models.tenant import Tenant
from src.models.api_key import ApiKey
from src.mcp.tools import (
    generate_content_tool,
    ingest_document_tool,
    get_voice_profile,
    set_voice_profile,
    check_usage
)

# Extract original functions from FastMCP tools if they are wrapped, but in python typically we can just call them.
# Let's assume they can be called directly or we use the unwrapped functions. FastMCP tools might be callable.

@pytest.fixture
async def sample_tenant(async_session):
    tenant = Tenant(name="Test Tenant")
    async_session.add(tenant)
    await async_session.commit()
    await async_session.refresh(tenant)
    return tenant

@pytest.fixture
async def sample_client(async_session, sample_tenant):
    client = Client(name="Test Client", tenant_id=sample_tenant.id)
    async_session.add(client)
    await async_session.commit()
    await async_session.refresh(client)
    return client

@pytest.fixture
async def mcp_setup(async_session, sample_tenant, sample_client):
    from src.repositories.api_key_repo import create_api_key
    api_key_obj, raw_key = await create_api_key(async_session, sample_tenant.id, "test_key")
    await async_session.commit()
    return {"api_key": raw_key, "client_id": str(sample_client.id)}

@pytest.mark.asyncio
async def test_generate_content_tool_returns_draft(mcp_setup):
    api_key = mcp_setup["api_key"]
    client_id = mcp_setup["client_id"]
    
    result = await generate_content_tool(api_key=api_key, client_id=client_id, brief="A test brief")
    assert "Draft:" in result
    assert "Sources:" in result

@pytest.mark.asyncio
async def test_ingest_document_tool(mcp_setup):
    api_key = mcp_setup["api_key"]
    client_id = mcp_setup["client_id"]
    
    result = await ingest_document_tool(
        api_key=api_key,
        client_id=client_id,
        source_type="text",
        content="This is a test content",
        title="Test Doc"
    )
    assert "Ingested" in result
    assert "chunks from document 'Test Doc'" in result

@pytest.mark.asyncio
async def test_get_voice_profile_no_profile(mcp_setup):
    api_key = mcp_setup["api_key"]
    client_id = mcp_setup["client_id"]
    
    result = await get_voice_profile(api_key=api_key, client_id=client_id)
    assert result == "No voice profile set."

@pytest.mark.asyncio
async def test_set_and_get_voice_profile(mcp_setup):
    api_key = mcp_setup["api_key"]
    client_id = mcp_setup["client_id"]
    
    set_result = await set_voice_profile(
        api_key=api_key,
        client_id=client_id,
        tone="professional",
        pov="first_person"
    )
    assert "Voice profile updated" in set_result
    
    get_result = await get_voice_profile(api_key=api_key, client_id=client_id)
    assert "Tone: professional" in get_result
    assert "POV: first_person" in get_result

@pytest.mark.asyncio
async def test_invalid_api_key():
    result = await check_usage(api_key="invalid_key", client_id=str(uuid.uuid4()))
    assert "Error:" in result
    assert "Invalid API key" in result
