from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import TYPE_CHECKING
from uuid import UUID
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException

from src.agent import AgentDeps, run_generation
from src.core.config import settings
from src.repositories import generation_repo
from src.repositories import voice_profile_repo
from src.services.voice_profile import (
    get_voice_profile_prompt_fragment,
    validate_voice_profile_constraints
)
from src.models.generation_request import GenerationRequest
from src.services import byok

if TYPE_CHECKING:
    from src.models.client import Client
    from src.models.tenant import Tenant

async def check_and_increment_usage(session: AsyncSession, client: "Client") -> None:
    """Enforces usage caps for default-key clients with a 30-day reset window."""
    if client.llm_api_key_encrypted is not None:
        return  # BYOK clients skip usage caps

    # Refetch client with row-level lock
    from src.models.client import Client
    stmt = select(Client).where(Client.id == client.id).with_for_update()
    result = await session.execute(stmt)
    locked_client = result.scalar_one()

    now = datetime.now(timezone.utc)
    if locked_client.usage_reset_at is None or locked_client.usage_reset_at < (now - timedelta(days=30)):
        locked_client.usage_this_month = 0
        locked_client.usage_reset_at = now

    if locked_client.usage_cap is not None and locked_client.usage_this_month >= locked_client.usage_cap:
        raise HTTPException(status_code=429, detail="Monthly usage cap reached")

    locked_client.usage_this_month += 1
    
    # Update the passed client object for consistency in the current request
    client.usage_this_month = locked_client.usage_this_month
    client.usage_reset_at = locked_client.usage_reset_at


async def generate_content(
    session: AsyncSession, client: "Client", tenant: "Tenant", brief: str
) -> GenerationRequest:
    # Create the pending request in DB
    gen_request = await generation_repo.create_generation_request(
        session=session,
        tenant_id=tenant.id,
        client_id=client.id,
        brief=brief
    )
    
    try:
        # Enforce usage cap
        await check_and_increment_usage(session, client)

        # Resolve model
        model_id, api_key = byok.resolve_model_for_client(client)

        # Load voice profile fragment
        vp_fragment = await get_voice_profile_prompt_fragment(session, client.id)
        
        # Build deps
        deps = AgentDeps(
            session=session,
            client_id=client.id,
            tenant_id=tenant.id,
            voice_profile_fragment=vp_fragment,
            tavily_api_key=settings.TAVILY_API_KEY or ""
        )
        
        # Run agent
        draft_text, sources_list = await run_generation(deps, brief, model_id=model_id, api_key=api_key)
        
        # Validation
        error_msg = None
        profile = await voice_profile_repo.get_voice_profile(session, client.id)
        if profile:
            violations = await validate_voice_profile_constraints(profile, draft_text)
            if violations:
                error_msg = f"Voice profile constraint violations: used banned words/phrases: {', '.join(violations)}"
        
        # Update request
        updated_request = await generation_repo.update_generation_request(
            session=session,
            request_id=gen_request.id,
            output=draft_text,
            sources_used=sources_list,
            llm_model_used=model_id,
            llm_provider_used=client.llm_provider or "google",

            status="completed",
            error_message=error_msg
        )
        
        return updated_request
        
    except Exception as e:
        # Handle failures gracefully by updating the request
        updated_request = await generation_repo.update_generation_request(
            session=session,
            request_id=gen_request.id,
            status="failed",
            error_message=str(e)
        )
        raise
