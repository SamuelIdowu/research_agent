import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta, timezone
from src.models.tenant import Tenant
import asyncio

pytestmark = pytest.mark.asyncio

async def test_health_no_auth(async_client: AsyncClient) -> None:
    response = await async_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

async def test_missing_api_key(async_client: AsyncClient) -> None:
    response = await async_client.get("/tenants")
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid API key"}

async def test_invalid_api_key(async_client: AsyncClient) -> None:
    response = await async_client.get("/tenants", headers={"X-Api-Key": "ra_fakekey123"})
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid API key"}

async def test_valid_api_key(async_client: AsyncClient, async_session: AsyncSession) -> None:
    # Create tenant and get key
    resp = await async_client.post("/tenants", json={"name": "AuthTestTenant"})
    assert resp.status_code == 201
    raw_key = resp.json()["raw_api_key"]
    
    # Try accessing tenants list
    resp2 = await async_client.get("/tenants", headers={"X-Api-Key": raw_key})
    assert resp2.status_code == 200

async def test_revoked_api_key(async_client: AsyncClient, async_session: AsyncSession) -> None:
    resp = await async_client.post("/tenants", json={"name": "RevokeTestTenant"})
    raw_key = resp.json()["raw_api_key"]
    tenant_id = resp.json()["id"]
    
    # Revoke key manually in DB for test
    from src.repositories.api_key_repo import list_for_tenant, revoke
    keys = await list_for_tenant(async_session, tenant_id)
    await revoke(async_session, keys[0].id, tenant_id)
    await async_session.commit()
    
    resp2 = await async_client.get("/tenants", headers={"X-Api-Key": raw_key})
    assert resp2.status_code == 401

async def test_rate_limiting(async_client: AsyncClient, async_session: AsyncSession) -> None:
    resp = await async_client.post("/tenants", json={"name": "RateLimitTenant"})
    raw_key = resp.json()["raw_api_key"]
    
    # Send 60 requests
    for i in range(60):
        r = await async_client.get("/tenants", headers={"X-Api-Key": raw_key})
        assert r.status_code == 200, f"Request {i+1} failed"
        
    for i in range(5):
        r = await async_client.get("/tenants", headers={"X-Api-Key": raw_key})
        assert r.status_code == 429, f"Request {60+i+1} didn't rate limit"

async def test_rate_limit_window_reset(async_client: AsyncClient, async_session: AsyncSession) -> None:
    resp = await async_client.post("/tenants", json={"name": "WindowResetTenant"})
    raw_key = resp.json()["raw_api_key"]
    tenant_id = resp.json()["id"]
    
    # Send 60 requests
    for i in range(60):
        r = await async_client.get("/tenants", headers={"X-Api-Key": raw_key})
        assert r.status_code == 200
        
    r = await async_client.get("/tenants", headers={"X-Api-Key": raw_key})
    assert r.status_code == 429
    
    # Shift window start manually
    from sqlalchemy import update
    stmt = update(Tenant).where(Tenant.id == tenant_id).values(
        rate_limit_window_start=datetime.now(timezone.utc) - timedelta(seconds=65)
    )
    await async_session.execute(stmt)
    await async_session.commit()
    
    # Should be allowed again
    r = await async_client.get("/tenants", headers={"X-Api-Key": raw_key})
    assert r.status_code == 200
