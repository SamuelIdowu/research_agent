import pytest
from httpx import AsyncClient
from src.mcp.tools import generate_content_tool, ingest_document_tool
from src.models.client import Client
from src.models.tenant import Tenant

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
async def mcp_parity_setup(async_session, sample_tenant, sample_client):
    from src.repositories.api_key_repo import create_api_key
    api_key_obj, raw_key = await create_api_key(async_session, sample_tenant.id, "test_key")
    await async_session.commit()
    return {"api_key": raw_key, "client_id": str(sample_client.id)}

@pytest.mark.asyncio
@pytest.mark.integration
async def test_mcp_parity_generate_content(mcp_parity_setup, async_client: AsyncClient):
    api_key = mcp_parity_setup["api_key"]
    client_id = mcp_parity_setup["client_id"]
    brief = "Parity test brief"

    # 1. REST Call
    rest_resp = await async_client.post(
        "/generate",
        json={"client_id": client_id, "brief": brief},
        headers={"X-Api-Key": api_key}
    )
    assert rest_resp.status_code == 200
    rest_data = rest_resp.json()
    assert rest_data["status"] == "completed"

    # 2. MCP Call
    mcp_result = await generate_content_tool(api_key=api_key, client_id=client_id, brief=brief)
    
    # 3. Assertions
    assert "Draft:" in mcp_result
    assert "Sources:" in mcp_result
    assert "Error" not in mcp_result

@pytest.mark.asyncio
@pytest.mark.integration
async def test_mcp_parity_ingest_document(mcp_parity_setup, async_client: AsyncClient, async_session):
    api_key = mcp_parity_setup["api_key"]
    client_id = mcp_parity_setup["client_id"]
    
    # 1. REST Call
    rest_resp = await async_client.post(
        "/documents",
        json={
            "client_id": client_id,
            "source_type": "text",
            "content": "REST content block",
            "title": "REST Doc"
        },
        headers={"X-Api-Key": api_key}
    )
    assert rest_resp.status_code == 201
    rest_data = rest_resp.json()
    assert rest_data["status"] == "ready"

    # 2. MCP Call
    mcp_result = await ingest_document_tool(
        api_key=api_key,
        client_id=client_id,
        source_type="text",
        content="REST content block",
        title="MCP Doc"
    )
    
    # 3. Assertions
    assert "Ingested 1 chunks" in mcp_result
    assert "Status: ready" in mcp_result
