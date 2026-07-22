import pytest
from typing import Any
from src.services.analytics import log_event

@pytest.fixture
async def tenant(async_client: Any) -> Any:
    response = await async_client.post("/tenants", json={"name": "Analytics Test Tenant"})
    return response.json()

@pytest.fixture
async def client_fixture(async_client: Any, tenant: Any) -> Any:
    response = await async_client.post("/clients", json={
        "tenant_id": tenant["id"],
        "name": "Analytics Test Client",
        "usage_cap": 100
    }, headers={"X-Api-Key": tenant["raw_api_key"]})
    return response.json()

@pytest.mark.asyncio
async def test_read_tenant_metrics(async_client: Any, tenant: Any, client_fixture: Any, async_session: Any) -> None:
    # Log some events directly via service layer to populate DB
    import uuid
    tenant_id = uuid.UUID(tenant["id"])
    client_id = uuid.UUID(client_fixture["id"])
    
    await log_event(async_session, tenant_id, client_id, "api_event", duration_ms=150, tokens_used=75)
    
    response = await async_client.get("/analytics/tenant", headers={"X-Api-Key": tenant["raw_api_key"]})
    assert response.status_code == 200
    data = response.json()
    assert data["tenant_id"] == str(tenant_id)
    assert data["metrics"]["total_events"] == 1
    assert data["metrics"]["total_tokens_used"] == 75
    assert data["metrics"]["avg_duration_ms"] == 150.0

@pytest.mark.asyncio
async def test_read_client_metrics(async_client: Any, tenant: Any, client_fixture: Any, async_session: Any) -> None:
    import uuid
    tenant_id = uuid.UUID(tenant["id"])
    client_id = uuid.UUID(client_fixture["id"])
    
    await log_event(async_session, tenant_id, client_id, "api_event", duration_ms=200, tokens_used=100)
    
    response = await async_client.get(f"/analytics/clients/{str(client_id)}", headers={"X-Api-Key": tenant["raw_api_key"]})
    assert response.status_code == 200
    data = response.json()
    assert data["tenant_id"] == str(tenant_id)
    assert data["client_id"] == str(client_id)
    assert data["metrics"]["total_events"] == 1
    assert data["metrics"]["total_tokens_used"] == 100
    assert data["metrics"]["avg_duration_ms"] == 200.0
