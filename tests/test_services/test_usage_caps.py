import pytest
from datetime import datetime, timedelta, timezone
from src.services import generation
from src.models.client import Client
from src.models.tenant import Tenant
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

async def create_test_client(async_session: AsyncSession, **client_kwargs) -> Client:
    tenant_id = uuid.uuid4()
    tenant = Tenant(id=tenant_id, name="Test Tenant")
    async_session.add(tenant)
    
    client_kwargs.setdefault("id", uuid.uuid4())
    client_kwargs.setdefault("name", "Test Client")
    client_kwargs.setdefault("tenant_id", tenant_id)
    
    client = Client(**client_kwargs)
    async_session.add(client)
    await async_session.commit()
    return client

@pytest.mark.asyncio
async def test_check_and_increment_usage_success(async_session: AsyncSession) -> None:
    recent_reset_date = datetime.now(timezone.utc) - timedelta(days=1)
    client = await create_test_client(async_session, usage_cap=10, usage_this_month=5, usage_reset_at=recent_reset_date)

    # Call check
    await generation.check_and_increment_usage(async_session, client)
    await async_session.commit()
    
    # Reload and verify
    await async_session.refresh(client)
    assert client.usage_this_month == 6

@pytest.mark.asyncio
async def test_check_and_increment_usage_exceeded(async_session: AsyncSession) -> None:
    recent_reset_date = datetime.now(timezone.utc) - timedelta(days=1)
    client = await create_test_client(async_session, usage_cap=10, usage_this_month=10, usage_reset_at=recent_reset_date)

    with pytest.raises(HTTPException) as excinfo:
        await generation.check_and_increment_usage(async_session, client)
    
    assert excinfo.value.status_code == 429
    assert "Monthly usage cap reached" in str(excinfo.value.detail)
    
    await async_session.refresh(client)
    assert client.usage_this_month == 10

@pytest.mark.asyncio
async def test_check_and_increment_usage_rolling_window(async_session: AsyncSession) -> None:
    old_reset_date = datetime.now(timezone.utc) - timedelta(days=31)
    client = await create_test_client(async_session, usage_cap=10, usage_this_month=10, usage_reset_at=old_reset_date)

    # The usage should reset and increment to 1
    await generation.check_and_increment_usage(async_session, client)
    await async_session.commit()
    
    await async_session.refresh(client)
    assert client.usage_this_month == 1
    assert client.usage_reset_at is not None
    assert client.usage_reset_at > old_reset_date

@pytest.mark.asyncio
async def test_check_and_increment_usage_byok_bypass(async_session: AsyncSession) -> None:
    recent_reset_date = datetime.now(timezone.utc) - timedelta(days=1)
    # A BYOK client has an encrypted API key
    client = await create_test_client(
        async_session, 
        usage_cap=10, 
        usage_this_month=10, 
        usage_reset_at=recent_reset_date,
        llm_api_key_encrypted="encrypted_key_data"
    )

    # Calling check_and_increment_usage should NOT raise an HTTPException, even though usage_this_month is at cap
    await generation.check_and_increment_usage(async_session, client)
    await async_session.commit()
    
    # Reload and verify usage didn't increment
    await async_session.refresh(client)
    assert client.usage_this_month == 10
