import pytest
from typing import Any, AsyncGenerator
from httpx import ASGITransport, AsyncClient
from src.main import app
from src.models.tenant import Tenant
from sqlalchemy import select

@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client

@pytest.mark.asyncio
async def test_create_tenant_success(async_client: Any, async_session: Any) -> None:
    response = await async_client.post("/tenants", json={"name": "Test Tenant"})
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Tenant"
    assert "raw_api_key" in data
    assert "api_key_hash" not in data

@pytest.mark.asyncio
async def test_create_tenant_duplicate_name(async_client: Any, async_session: Any) -> None:
    # First creation
    response1 = await async_client.post("/tenants", json={"name": "Duplicate"})
    assert response1.status_code == 201
    
    # Second creation
    response2 = await async_client.post("/tenants", json={"name": "Duplicate"})
    assert response2.status_code == 409
    assert response2.json()["detail"] == "Tenant with this name already exists"

@pytest.mark.asyncio
async def test_list_tenants(async_client: Any, async_session: Any) -> None:
    # Create 3 tenants
    for i in range(3):
        await async_client.post("/tenants", json={"name": f"List Tenant {i}"})
    
    response = await async_client.get("/tenants")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 3
    assert len(data["items"]) >= 3

@pytest.mark.asyncio
async def test_get_tenant_by_id(async_client: Any, async_session: Any) -> None:
    create_response = await async_client.post("/tenants", json={"name": "Get By Id"})
    tenant_id = create_response.json()["id"]

    response = await async_client.get(f"/tenants/{tenant_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == tenant_id
    assert data["name"] == "Get By Id"
    assert "api_key_hash" not in data
    assert "raw_api_key" not in data

@pytest.mark.asyncio
async def test_get_tenant_not_found(async_client: Any, async_session: Any) -> None:
    fake_id = "00000000-0000-0000-0000-000000000000"
    response = await async_client.get(f"/tenants/{fake_id}")
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_deactivate_tenant(async_client: Any, async_session: Any) -> None:
    create_response = await async_client.post("/tenants", json={"name": "To Deactivate"})
    tenant_id = create_response.json()["id"]

    response = await async_client.delete(f"/tenants/{tenant_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["is_active"] is False

    # Check database
    stmt = select(Tenant).where(Tenant.id == tenant_id)
    result = await async_session.execute(stmt)
    tenant = result.scalar_one()
    assert tenant.is_active is False
