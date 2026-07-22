import pytest
import uuid
from src.services.analytics import log_event, get_tenant_metrics, get_client_metrics
from src.models.tenant import Tenant
from src.models.client import Client

@pytest.mark.asyncio
async def test_log_event(async_session):
    tenant = Tenant(name=f"Test Tenant {uuid.uuid4().hex}")
    async_session.add(tenant)
    await async_session.commit()
    
    client = Client(tenant_id=tenant.id, name="Test Client", usage_cap=100)
    async_session.add(client)
    await async_session.commit()
    
    tenant_id = tenant.id
    client_id = client.id
    
    event = await log_event(
        session=async_session,
        tenant_id=tenant_id,
        client_id=client_id,
        event_name="test_event",
        duration_ms=100,
        tokens_used=50,
        metadata={"test": "data"}
    )
    
    assert event.id is not None
    assert event.tenant_id == tenant_id
    assert event.client_id == client_id
    assert event.event_name == "test_event"
    assert event.duration_ms == 100
    assert event.tokens_used == 50
    assert event.metadata_ == {"test": "data"}

@pytest.mark.asyncio
async def test_get_tenant_metrics(async_session):
    tenant = Tenant(name=f"Test Tenant {uuid.uuid4().hex}")
    async_session.add(tenant)
    await async_session.commit()
    
    client = Client(tenant_id=tenant.id, name="Test Client", usage_cap=100)
    async_session.add(client)
    await async_session.commit()
    
    tenant_id = tenant.id
    client_id = client.id
    
    await log_event(async_session, tenant_id, client_id, "event1", duration_ms=100, tokens_used=50)
    await log_event(async_session, tenant_id, client_id, "event2", duration_ms=200, tokens_used=100)
    
    metrics = await get_tenant_metrics(async_session, tenant_id)
    assert metrics["total_events"] == 2
    assert metrics["total_tokens_used"] == 150
    assert metrics["avg_duration_ms"] == 150.0

@pytest.mark.asyncio
async def test_get_client_metrics(async_session):
    tenant = Tenant(name=f"Test Tenant {uuid.uuid4().hex}")
    async_session.add(tenant)
    await async_session.commit()
    
    client1 = Client(tenant_id=tenant.id, name="Test Client 1", usage_cap=100)
    client2 = Client(tenant_id=tenant.id, name="Test Client 2", usage_cap=100)
    async_session.add_all([client1, client2])
    await async_session.commit()
    
    tenant_id = tenant.id
    client1_id = client1.id
    client2_id = client2.id
    
    await log_event(async_session, tenant_id, client1_id, "event1", duration_ms=100, tokens_used=50)
    await log_event(async_session, tenant_id, client2_id, "event2", duration_ms=200, tokens_used=100)
    
    metrics1 = await get_client_metrics(async_session, tenant_id, client1_id)
    assert metrics1["total_events"] == 1
    assert metrics1["total_tokens_used"] == 50
    assert metrics1["avg_duration_ms"] == 100.0

    metrics2 = await get_client_metrics(async_session, tenant_id, client2_id)
    assert metrics2["total_events"] == 1
    assert metrics2["total_tokens_used"] == 100
    assert metrics2["avg_duration_ms"] == 200.0
