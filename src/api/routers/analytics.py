from datetime import datetime
import uuid
from typing import Any

from fastapi import APIRouter, Depends, Query

from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import get_db
from src.api.dependencies import get_current_tenant
from src.models.tenant import Tenant
from src.services.analytics import get_tenant_metrics, get_client_metrics

router = APIRouter(tags=["analytics"])

@router.get("/tenant")
async def read_tenant_metrics(
    start_date: datetime | None = Query(None),
    end_date: datetime | None = Query(None),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    metrics = await get_tenant_metrics(db, tenant.id, start_date, end_date)
    return {
        "tenant_id": tenant.id,
        "metrics": metrics
    }

@router.get("/clients/{client_id}")
async def read_client_metrics(
    client_id: uuid.UUID,
    start_date: datetime | None = Query(None),
    end_date: datetime | None = Query(None),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    # Metrics service inherently enforces tenant_id + client_id
    metrics = await get_client_metrics(db, tenant.id, client_id, start_date, end_date)
    return {
        "tenant_id": tenant.id,
        "client_id": client_id,
        "metrics": metrics
    }
