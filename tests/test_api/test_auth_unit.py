import pytest
import uuid
from datetime import datetime, timezone, timedelta
from fastapi import Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import MagicMock

from src.api.middleware.auth import authenticate_and_rate_limit
from src.core.security import hash_api_key
from src.models.tenant import Tenant
from src.models.api_key import ApiKey
from src.repositories.tenant_repo import create_tenant

pytestmark = pytest.mark.asyncio

async def test_auth_missing_header(async_session: AsyncSession) -> None:
    request = MagicMock(spec=Request)
    request.headers = {}
    with pytest.raises(HTTPException) as excinfo:
        await authenticate_and_rate_limit(request, async_session, request.headers.get("X-Api-Key"))
    assert excinfo.value.status_code == 401

async def test_auth_invalid_header(async_session: AsyncSession) -> None:
    request = MagicMock(spec=Request)
    request.headers = {"X-Api-Key": "invalid_key"}
    with pytest.raises(HTTPException) as excinfo:
        await authenticate_and_rate_limit(request, async_session, request.headers.get("X-Api-Key"))
    assert excinfo.value.status_code == 401

async def test_auth_success(async_session: AsyncSession) -> None:
    tenant, raw_key = await create_tenant(async_session, "UnitTestTenant")
    await async_session.commit()
    
    request = MagicMock(spec=Request)
    request.headers = {"X-Api-Key": raw_key}
    request.state = MagicMock()
    
    auth_tenant = await authenticate_and_rate_limit(request, async_session, request.headers.get("X-Api-Key"))
    assert auth_tenant.id == tenant.id
    assert auth_tenant.request_count_this_minute == 1

async def test_auth_suspended_tenant(async_session: AsyncSession) -> None:
    tenant, raw_key = await create_tenant(async_session, "SuspendedTenant")
    tenant.is_active = False
    await async_session.commit()
    
    request = MagicMock(spec=Request)
    request.headers = {"X-Api-Key": raw_key}
    request.state = MagicMock()
    
    with pytest.raises(HTTPException) as excinfo:
        await authenticate_and_rate_limit(request, async_session, request.headers.get("X-Api-Key"))
    assert excinfo.value.status_code == 401
    assert "suspended" in excinfo.value.detail.lower()

async def test_auth_rate_limiting(async_session: AsyncSession) -> None:
    tenant, raw_key = await create_tenant(async_session, "RateLimitTenant")
    tenant.rate_limit_per_minute = 2
    await async_session.commit()
    
    request = MagicMock(spec=Request)
    request.headers = {"X-Api-Key": raw_key}
    request.state = MagicMock()
    
    # Request 1: success
    t1 = await authenticate_and_rate_limit(request, async_session, request.headers.get("X-Api-Key"))
    assert t1.request_count_this_minute == 1
    
    # Request 2: success
    t2 = await authenticate_and_rate_limit(request, async_session, request.headers.get("X-Api-Key"))
    assert t2.request_count_this_minute == 2
    
    # Request 3: fail
    with pytest.raises(HTTPException) as excinfo:
        await authenticate_and_rate_limit(request, async_session, request.headers.get("X-Api-Key"))
    assert excinfo.value.status_code == 429

async def test_auth_rate_limit_reset(async_session: AsyncSession) -> None:
    tenant, raw_key = await create_tenant(async_session, "RateLimitResetTenant")
    tenant.rate_limit_per_minute = 1
    tenant.rate_limit_window_start = datetime.now(timezone.utc) - timedelta(seconds=65)
    tenant.request_count_this_minute = 1
    await async_session.commit()
    
    request = MagicMock(spec=Request)
    request.headers = {"X-Api-Key": raw_key}
    request.state = MagicMock()
    
    # Window should reset, so request count goes back to 1
    t = await authenticate_and_rate_limit(request, async_session, request.headers.get("X-Api-Key"))
    assert t.request_count_this_minute == 1
