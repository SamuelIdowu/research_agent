import pytest
from typing import Any, AsyncGenerator
from httpx import ASGITransport, AsyncClient
from src.main import app

@pytest.fixture
async def tenant(async_client: Any) -> Any:
    response = await async_client.post("/tenants", json={"name": "Client Test Tenant"})
    return response.json()

@pytest.fixture
async def tenant_2(async_client: Any) -> Any:
    response = await async_client.post("/tenants", json={"name": "Client Test Tenant 2"})
    return response.json()

@pytest.mark.asyncio
async def test_create_client_success(async_client: Any, tenant: Any) -> None:
    response = await async_client.post("/clients", json={
        "tenant_id": tenant["id"],
        "name": "Test Client",
        "usage_cap": 100
    }, headers={"X-Api-Key": tenant["raw_api_key"]})
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Client"
    assert data["usage_cap"] == 100
    assert data["tenant_id"] == tenant["id"]

@pytest.mark.asyncio
async def test_create_client_invalid_tenant(async_client: Any) -> None:
    fake_id = "00000000-0000-0000-0000-000000000000"
    # Create an auth tenant just to get a valid API key for the request
    auth_resp = await async_client.post("/tenants", json={"name": "Auth Tenant"})
    api_key = auth_resp.json()["raw_api_key"]
    auth_tenant_id = auth_resp.json()["id"]

    response = await async_client.post("/clients", json={
        "tenant_id": fake_id,
        "name": "Test Client",
        "usage_cap": 100
    }, headers={"X-Api-Key": api_key})
    assert response.status_code == 201
    assert response.json()["tenant_id"] == auth_tenant_id

@pytest.mark.asyncio
async def test_list_clients_scoped_to_tenant(async_client: Any, tenant: Any, tenant_2: Any) -> None:
    # Create clients in tenant 1
    await async_client.post("/clients", json={"tenant_id": tenant["id"], "name": "C1"}, headers={"X-Api-Key": tenant["raw_api_key"]})
    await async_client.post("/clients", json={"tenant_id": tenant["id"], "name": "C2"}, headers={"X-Api-Key": tenant["raw_api_key"]})
    
    # Create client in tenant 2
    await async_client.post("/clients", json={"tenant_id": tenant_2["id"], "name": "C3"}, headers={"X-Api-Key": tenant_2["raw_api_key"]})

    # Check tenant 1
    response = await async_client.get(f"/clients?tenant_id={tenant['id']}", headers={"X-Api-Key": tenant["raw_api_key"]})
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2

    # Check tenant 2
    response2 = await async_client.get(f"/clients?tenant_id={tenant_2['id']}", headers={"X-Api-Key": tenant_2["raw_api_key"]})
    assert response2.status_code == 200
    data2 = response2.json()
    assert data2["total"] == 1

@pytest.mark.asyncio
async def test_update_client(async_client: Any, tenant: Any) -> None:
    create_resp = await async_client.post("/clients", json={
        "tenant_id": tenant["id"],
        "name": "Old Name",
        "usage_cap": 50
    }, headers={"X-Api-Key": tenant["raw_api_key"]})
    client_id = create_resp.json()["id"]

    response = await async_client.patch(f"/clients/{client_id}?tenant_id={tenant['id']}", json={
        "name": "New Name",
        "usage_cap": 100
    }, headers={"X-Api-Key": tenant["raw_api_key"]})
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "New Name"
    assert data["usage_cap"] == 100

@pytest.mark.asyncio
async def test_deactivate_client(async_client: Any, tenant: Any) -> None:
    create_resp = await async_client.post("/clients", json={
        "tenant_id": tenant["id"],
        "name": "To Deactivate"
    }, headers={"X-Api-Key": tenant["raw_api_key"]})
    client_id = create_resp.json()["id"]

    response = await async_client.delete(f"/clients/{client_id}?tenant_id={tenant['id']}", headers={"X-Api-Key": tenant["raw_api_key"]})
    assert response.status_code == 200
    assert response.json()["is_active"] is False

@pytest.mark.asyncio
async def test_encrypted_key_never_in_response(async_client: Any, tenant: Any) -> None:
    create_resp = await async_client.post("/clients", json={
        "tenant_id": tenant["id"],
        "name": "No Key Client"
    }, headers={"X-Api-Key": tenant["raw_api_key"]})
    data = create_resp.json()
    assert "llm_api_key_encrypted" not in data
    
    # Also check GET request
    get_resp = await async_client.get(f"/clients/{data['id']}?tenant_id={tenant['id']}", headers={"X-Api-Key": tenant["raw_api_key"]})
    assert "llm_api_key_encrypted" not in get_resp.json()
