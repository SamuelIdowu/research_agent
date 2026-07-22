import pytest
from httpx import AsyncClient
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import patch
from src.main import app
from src.repositories import tenant_repo, client_repo
from src.schemas.client import ClientCreate
from src.schemas.tenant import TenantCreate
from src.api.dependencies import get_current_tenant
from src.models.tenant import Tenant

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

@pytest.mark.asyncio
@patch("src.services.generation.run_generation")
async def test_generate_end_to_end(
    mock_run_generation,
    async_client: AsyncClient,
    sample_client,
    async_session: AsyncSession
):
    # Setup mock
    tenant = await async_session.get(Tenant, sample_client.tenant_id)
    app.dependency_overrides[get_current_tenant] = lambda: tenant
    
    mock_run_generation.return_value = ("Draft content here.", [{"type": "kb", "excerpt": "Test"}], 100, 50)
    
    # Run API call
    response = await async_client.post(
        "/generate",
        json={"brief": "Test brief", "client_id": str(sample_client.id)}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["draft"] == "Draft content here."
    assert "request_id" in data
    
    request_id = data["request_id"]
    
    # Test GET generation
    response2 = await async_client.get(f"/generations/{request_id}")
    assert response2.status_code == 200
    assert response2.json()["request_id"] == request_id
    assert response2.json()["brief"] == "Test brief"

@pytest.mark.asyncio
async def test_generate_wrong_client(
    async_client: AsyncClient,
    async_session: AsyncSession
):
    # Setup mock tenant
    app.dependency_overrides[get_current_tenant] = lambda: Tenant(id=uuid4(), name="Other")
    
    # Run API call with non-existent client ID
    response = await async_client.post(
        "/generate",
        json={"brief": "Test", "client_id": str(uuid4())}
    )
    
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_generate_empty_brief(
    async_client: AsyncClient
):
    app.dependency_overrides[get_current_tenant] = lambda: Tenant(id=uuid4(), name="Test")
    
    # Run API call with missing/empty brief
    response = await async_client.post(
        "/generate",
        json={"brief": "", "client_id": str(uuid4())}
    )
    
    # Should fail validation (empty brief)
    # The BaseModel currently accepts empty string unless restricted, let's assume it passes schema but might fail downstream or fail schema if min_length=1
    # For now Pydantic field is just max_length=5000. Wait, Sprint 06 spec says empty brief -> 422.
    assert response.status_code == 422
