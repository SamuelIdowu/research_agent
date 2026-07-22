from typing import cast
from datetime import datetime, timezone
from fastapi import Request, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.security import hash_api_key
from src.models.api_key import ApiKey
from src.models.tenant import Tenant

async def authenticate_and_rate_limit(request: Request, session: AsyncSession, api_key_header: str | None) -> Tenant:
    """Authenticates the API key and enforces per-tenant rate limiting."""
    if not api_key_header:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    key_hash = hash_api_key(api_key_header)
    
    # We join Tenant to load it and lock the tenant row for rate limiting using with_for_update
    stmt = (
        select(ApiKey, Tenant)
        .join(Tenant)
        .where(ApiKey.key_hash == key_hash)
        .with_for_update(of=Tenant)
    )
    result = await session.execute(stmt)
    row = result.first()
    
    if not row:
        raise HTTPException(status_code=401, detail="Invalid API key")
        
    api_key = cast(ApiKey, row[0])
    tenant = cast(Tenant, row[1])
    
    if not api_key.is_active:
        raise HTTPException(status_code=401, detail="Invalid API key")
        
    if not tenant.is_active:
        raise HTTPException(status_code=401, detail="Tenant suspended")
        
    # Enforce Rate Limiting
    now = datetime.now(timezone.utc)
    if tenant.rate_limit_window_start is None:
        tenant.rate_limit_window_start = now
        tenant.request_count_this_minute = 1
    else:
        elapsed = (now - tenant.rate_limit_window_start).total_seconds()
        if elapsed > 60:
            tenant.rate_limit_window_start = now
            tenant.request_count_this_minute = 1
        else:
            tenant.request_count_this_minute += 1
            if tenant.request_count_this_minute > tenant.rate_limit_per_minute:
                # Still commit the last_used_at / counter changes before raising
                await session.commit()
                raise HTTPException(status_code=429, detail="Rate limit exceeded")
                
    api_key.last_used_at = now
    
    request.state.tenant = tenant
    # Commit changes from rate-limiting/last_used_at
    await session.commit()
    return tenant
