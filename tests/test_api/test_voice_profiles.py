import pytest
from typing import Any
from uuid import uuid4

@pytest.fixture
async def tenant(async_client: Any) -> Any:
    response = await async_client.post("/tenants", json={"name": f"VP Test Tenant {uuid4()}"})
    return response.json()

@pytest.fixture
async def client_obj(async_client: Any, tenant: Any) -> Any:
    response = await async_client.post("/clients", json={
        "tenant_id": tenant["id"],
        "name": f"VP Test Client {uuid4()}"
    }, headers={"X-Api-Key": tenant["raw_api_key"]})
    return response.json()

@pytest.fixture
async def tenant_2(async_client: Any) -> Any:
    response = await async_client.post("/tenants", json={"name": f"VP Test Tenant 2 {uuid4()}"})
    return response.json()

@pytest.mark.asyncio
async def test_set_voice_profile(async_client: Any, tenant: Any, client_obj: Any) -> None:
    payload = {
        "tone": "warm, expert",
        "pov": "first_person",
        "banned_words": ["spam", "synergy"],
        "extra_instructions": "Always be polite."
    }
    response = await async_client.put(
        f"/clients/{client_obj['id']}/voice-profile", 
        json=payload, 
        headers={"X-Api-Key": tenant["raw_api_key"]}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["tone"] == "warm, expert"
    assert data["pov"] == "first_person"
    assert data["banned_words"] == ["spam", "synergy"]
    assert data["extra_instructions"] == "Always be polite."
    assert "id" in data
    assert data["client_id"] == client_obj["id"]

@pytest.mark.asyncio
async def test_get_voice_profile(async_client: Any, tenant: Any, client_obj: Any) -> None:
    payload = {"tone": "warm"}
    await async_client.put(
        f"/clients/{client_obj['id']}/voice-profile", 
        json=payload, 
        headers={"X-Api-Key": tenant["raw_api_key"]}
    )
    
    response = await async_client.get(
        f"/clients/{client_obj['id']}/voice-profile", 
        headers={"X-Api-Key": tenant["raw_api_key"]}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["tone"] == "warm"

@pytest.mark.asyncio
async def test_update_voice_profile(async_client: Any, tenant: Any, client_obj: Any) -> None:
    payload = {"tone": "cold"}
    await async_client.put(
        f"/clients/{client_obj['id']}/voice-profile", 
        json=payload, 
        headers={"X-Api-Key": tenant["raw_api_key"]}
    )
    
    payload2 = {"tone": "warm", "banned_words": ["word"]}
    response = await async_client.put(
        f"/clients/{client_obj['id']}/voice-profile", 
        json=payload2, 
        headers={"X-Api-Key": tenant["raw_api_key"]}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["tone"] == "warm"
    assert data["banned_words"] == ["word"]

@pytest.mark.asyncio
async def test_delete_voice_profile(async_client: Any, tenant: Any, client_obj: Any) -> None:
    payload = {"tone": "warm"}
    await async_client.put(
        f"/clients/{client_obj['id']}/voice-profile", 
        json=payload, 
        headers={"X-Api-Key": tenant["raw_api_key"]}
    )
    
    delete_resp = await async_client.delete(
        f"/clients/{client_obj['id']}/voice-profile", 
        headers={"X-Api-Key": tenant["raw_api_key"]}
    )
    assert delete_resp.status_code == 204
    
    get_resp = await async_client.get(
        f"/clients/{client_obj['id']}/voice-profile", 
        headers={"X-Api-Key": tenant["raw_api_key"]}
    )
    assert get_resp.status_code == 404

@pytest.mark.asyncio
async def test_voice_profile_wrong_tenant(async_client: Any, tenant: Any, tenant_2: Any, client_obj: Any) -> None:
    # Try to PUT to client_obj with tenant_2's api key
    payload = {"tone": "warm"}
    response = await async_client.put(
        f"/clients/{client_obj['id']}/voice-profile", 
        json=payload, 
        headers={"X-Api-Key": tenant_2["raw_api_key"]}
    )
    # Should get 404 because the client won't be found under tenant_2
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_voice_profile_banned_words_list(async_client: Any, tenant: Any, client_obj: Any) -> None:
    payload = {
        "banned_words": [f"word{i}" for i in range(51)]
    }
    response = await async_client.put(
        f"/clients/{client_obj['id']}/voice-profile", 
        json=payload, 
        headers={"X-Api-Key": tenant["raw_api_key"]}
    )
    assert response.status_code == 422
