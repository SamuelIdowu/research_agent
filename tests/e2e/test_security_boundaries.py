import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_no_api_key_rejected_on_all_protected_routes(async_client: AsyncClient):
    routes = [
        ("GET", "/tenants"),
        ("POST", "/clients"),
        ("POST", "/documents"),
        ("POST", "/generate"),
        ("GET", "/generations/some_id"),
    ]
    for method, route in routes:
        response = await async_client.request(method, route)
        assert response.status_code == 401, f"{method} {route} should return 401 without API key"

@pytest.mark.asyncio
async def test_invalid_api_key_rejected(async_client: AsyncClient):
    headers = {"X-Api-Key": "invalid_key"}
    routes = [
        ("GET", "/tenants"),
        ("POST", "/clients"),
        ("POST", "/documents"),
        ("POST", "/generate"),
        ("GET", "/generations/some_id"),
    ]
    for method, route in routes:
        response = await async_client.request(method, route, headers=headers)
        assert response.status_code == 401, f"{method} {route} should return 401 with invalid API key"

@pytest.mark.asyncio
async def test_revoked_key_rejected(async_client: AsyncClient):
    # Create tenant and get key
    tenant_resp = await async_client.post("/tenants", json={"name": "Test Revoke Tenant"})
    assert tenant_resp.status_code == 201
    tenant_data = tenant_resp.json()
    tenant_id = tenant_data["id"]
    api_key = tenant_data["raw_api_key"]
    
    headers = {"X-Api-Key": api_key}
    
    # Verify key works
    client_resp = await async_client.post("/clients", json={"name": "Alice", "usage_cap": 10}, headers=headers)
    assert client_resp.status_code == 201
    
    # Revoke key (delete tenant)
    # Note: If there's an actual revoke endpoint, we should use it. For now, deleting tenant simulates revocation or invalidation.
    del_resp = await async_client.delete(f"/tenants/{tenant_id}", headers=headers)
    assert del_resp.status_code in (200, 204)
    
    # Verify key is rejected
    client_resp_after = await async_client.post("/clients", json={"name": "Bob", "usage_cap": 10}, headers=headers)
    assert client_resp_after.status_code == 401

@pytest.mark.asyncio
async def test_tenant_a_cannot_access_tenant_b_resources(async_client: AsyncClient):
    # Tenant A
    tenant_a_resp = await async_client.post("/tenants", json={"name": "Tenant A"})
    api_key_a = tenant_a_resp.json()["raw_api_key"]
    headers_a = {"X-Api-Key": api_key_a}
    
    # Tenant B
    tenant_b_resp = await async_client.post("/tenants", json={"name": "Tenant B"})
    api_key_b = tenant_b_resp.json()["raw_api_key"]
    headers_b = {"X-Api-Key": api_key_b}
    
    # A creates client
    client_a_resp = await async_client.post("/clients", json={"name": "Client A"}, headers=headers_a)
    client_a_id = client_a_resp.json()["id"]
    
    # B tries to get A's client
    get_client_b = await async_client.get(f"/clients/{client_a_id}", headers=headers_b)
    assert get_client_b.status_code == 404, "Tenant B should receive 404 when accessing Tenant A's client"
    
    # A creates document
    doc_a_resp = await async_client.post("/documents", json={"client_id": client_a_id, "source_type": "text", "content": "A doc"}, headers=headers_a)
    doc_a_id = doc_a_resp.json()["id"]
    
    # B tries to get A's document
    get_doc_b = await async_client.get(f"/documents/{doc_a_id}?client_id={client_a_id}", headers=headers_b)
    assert get_doc_b.status_code == 404, "Tenant B should receive 404 when accessing Tenant A's document"

@pytest.mark.asyncio
async def test_byok_key_never_exposed(async_client: AsyncClient):
    tenant_resp = await async_client.post("/tenants", json={"name": "BYOK Tenant"})
    api_key = tenant_resp.json()["raw_api_key"]
    headers = {"X-Api-Key": api_key}
    
    client_resp = await async_client.post("/clients", json={"name": "BYOK Client"}, headers=headers)
    client_id = client_resp.json()["id"]
    
    byok_resp = await async_client.post(
        f"/clients/{client_id}/byok",
        json={"llm_provider": "openai", "llm_model": "gpt-4o", "llm_api_key": "sk-dummy-key"},
        headers=headers
    )
    assert byok_resp.status_code == 200
    byok_data = byok_resp.json()
    assert "llm_api_key" not in byok_data
    assert "api_key" not in byok_data
    
    get_client = await async_client.get(f"/clients/{client_id}", headers=headers)
    get_data = get_client.json()
    assert "llm_api_key" not in get_data
    assert "api_key" not in get_data

@pytest.mark.asyncio
async def test_raw_api_key_only_returned_once(async_client: AsyncClient):
    tenant_resp = await async_client.post("/tenants", json={"name": "API Key Tenant"})
    tenant_data = tenant_resp.json()
    assert "raw_api_key" in tenant_data
    
    tenant_id = tenant_data["id"]
    get_resp = await async_client.get(f"/tenants/{tenant_id}")
    get_data = get_resp.json()
    assert "raw_api_key" not in get_data
