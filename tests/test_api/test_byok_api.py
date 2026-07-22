import pytest
from typing import Any
from cryptography.fernet import Fernet
from src.core.config import settings

# Setup dummy key for testing
settings.ENCRYPTION_SECRET_KEY = Fernet.generate_key().decode("utf-8")

@pytest.fixture
async def tenant(async_client: Any) -> Any:
    response = await async_client.post("/tenants", json={"name": "BYOK Test Tenant"})
    return response.json()

@pytest.fixture
async def client(async_client: Any, tenant: Any) -> Any:
    response = await async_client.post("/clients", json={
        "tenant_id": tenant["id"],
        "name": "BYOK Test Client"
    }, headers={"X-Api-Key": tenant["raw_api_key"]})
    return response.json()

@pytest.mark.asyncio
async def test_configure_byok_success(async_client: Any, tenant: Any, client: Any) -> None:
    response = await async_client.post(
        f"/clients/{client['id']}/byok?tenant_id={tenant['id']}",
        json={"llm_provider": "openai", "llm_model": "gpt-4", "llm_api_key": "sk-test-key"},
        headers={"X-Api-Key": tenant["raw_api_key"]}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["byok_configured"] is True
    # The API key should never be returned
    assert "llm_api_key_encrypted" not in data
    assert "llm_api_key" not in data

@pytest.mark.asyncio
async def test_remove_byok_success(async_client: Any, tenant: Any, client: Any) -> None:
    # First configure
    await async_client.post(
        f"/clients/{client['id']}/byok?tenant_id={tenant['id']}",
        json={"llm_provider": "openai", "llm_model": "gpt-4", "llm_api_key": "sk-test-key"},
        headers={"X-Api-Key": tenant["raw_api_key"]}
    )
    
    # Then remove
    response = await async_client.delete(
        f"/clients/{client['id']}/byok?tenant_id={tenant['id']}",
        headers={"X-Api-Key": tenant["raw_api_key"]}
    )
    assert response.status_code == 204
    
    # Fetch client to verify
    get_resp = await async_client.get(
        f"/clients/{client['id']}?tenant_id={tenant['id']}",
        headers={"X-Api-Key": tenant["raw_api_key"]}
    )
    data = get_resp.json()
    assert data["llm_provider"] is None
    assert data["llm_model"] is None
