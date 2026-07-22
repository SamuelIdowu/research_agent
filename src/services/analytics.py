from datetime import datetime
from typing import Any
import uuid

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.analytics_event import AnalyticsEvent
from src.models.generation_request import GenerationRequest

async def log_event(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    client_id: uuid.UUID,
    event_name: str,
    generation_request_id: uuid.UUID | None = None,
    duration_ms: int | None = None,
    tokens_used: int | None = None,
    metadata: dict[str, Any] | None = None,
) -> AnalyticsEvent:
    event = AnalyticsEvent(
        tenant_id=tenant_id,
        client_id=client_id,
        generation_request_id=generation_request_id,
        event_name=event_name,
        duration_ms=duration_ms,
        tokens_used=tokens_used,
        metadata_=metadata,
    )
    session.add(event)
    await session.commit()
    await session.refresh(event)
    return event

async def get_tenant_metrics(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> dict[str, Any]:
    # Construct base conditions
    conditions = [AnalyticsEvent.tenant_id == tenant_id]
    if start_date:
        conditions.append(AnalyticsEvent.created_at >= start_date)
    if end_date:
        conditions.append(AnalyticsEvent.created_at <= end_date)
        
    # Aggregate metrics
    stmt = select(
        func.count(AnalyticsEvent.id).label("total_events"),
        func.sum(AnalyticsEvent.tokens_used).label("total_tokens_used"),
        func.avg(AnalyticsEvent.duration_ms).label("avg_duration_ms")
    ).where(and_(*conditions))
    
    result = await session.execute(stmt)
    row = result.fetchone()
    
    return {
        "total_events": row.total_events if row else 0,
        "total_tokens_used": row.total_tokens_used if row and row.total_tokens_used else 0,
        "avg_duration_ms": float(row.avg_duration_ms) if row and row.avg_duration_ms else 0.0,
    }

async def get_client_metrics(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    client_id: uuid.UUID,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> dict[str, Any]:
    conditions = [AnalyticsEvent.tenant_id == tenant_id, AnalyticsEvent.client_id == client_id]
    if start_date:
        conditions.append(AnalyticsEvent.created_at >= start_date)
    if end_date:
        conditions.append(AnalyticsEvent.created_at <= end_date)
        
    stmt = select(
        func.count(AnalyticsEvent.id).label("total_events"),
        func.sum(AnalyticsEvent.tokens_used).label("total_tokens_used"),
        func.avg(AnalyticsEvent.duration_ms).label("avg_duration_ms")
    ).where(and_(*conditions))
    
    result = await session.execute(stmt)
    row = result.fetchone()
    
    return {
        "total_events": row.total_events if row else 0,
        "total_tokens_used": row.total_tokens_used if row and row.total_tokens_used else 0,
        "avg_duration_ms": float(row.avg_duration_ms) if row and row.avg_duration_ms else 0.0,
    }
