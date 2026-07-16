import uuid
from typing import Optional, List, Literal
from sqlalchemy import select

from src.mcp.server import mcp_server
from src.mcp.auth import get_mcp_tenant
from src.db.session import async_session_maker
from src.models.client import Client
from src.services.generation import generate_content
from src.services.ingestion import ingest_document
from src.repositories import voice_profile_repo

async def get_mcp_client(session, client_id_str: str, tenant) -> Client:
    """Helper to fetch a Client by ID and ensure it belongs to the tenant."""
    try:
        client_id = uuid.UUID(client_id_str)
    except ValueError:
        raise ValueError("Invalid client_id format")
    stmt = select(Client).where(Client.id == client_id, Client.tenant_id == tenant.id)
    result = await session.execute(stmt)
    client = result.scalar_one_or_none()
    if not client:
        raise ValueError("Client not found")
    return client

@mcp_server.tool()
async def generate_content_tool(api_key: str, client_id: str, brief: str) -> str:
    """Generate content draft based on a brief."""
    try:
        async with async_session_maker() as session:
            tenant = await get_mcp_tenant(api_key, session)
            client = await get_mcp_client(session, client_id, tenant)
            gen_request = await generate_content(session, client, tenant, brief)
            await session.commit()
            
            if gen_request.status == "failed":
                return f"Error generating content: {gen_request.error_message}"
                
            formatted_sources = "\n".join([f"- {s.get('url', s.get('title', 'Unknown'))}" for s in (gen_request.sources_used or []) if isinstance(s, dict)])
            return f"Draft:\n{gen_request.output}\n\nSources:\n{formatted_sources}"
    except Exception as e:
        return f"Error: {str(e)}"

@mcp_server.tool()
async def ingest_document_tool(
    api_key: str, 
    client_id: str, 
    source_type: str, 
    content: Optional[str] = None, 
    url: Optional[str] = None, 
    title: Optional[str] = None
) -> str:
    """Ingest a document into the client's knowledge base."""
    try:
        async with async_session_maker() as session:
            tenant = await get_mcp_tenant(api_key, session)
            client = await get_mcp_client(session, client_id, tenant)
            from src.repositories import document_repo
            document = await document_repo.create_document(
                session=session,
                client_id=client.id,
                tenant_id=client.tenant_id,
                source_type=source_type,
                title=title or "MCP Upload",
                source_url=url if source_type == "url" else None
            )
            
            chunks_count = await ingest_document(
                session=session,
                document_id=document.id,
                client_id=client.id,
                source_type=source_type,
                content=content,
                url=url
            )
            await session.commit()
            return f"Ingested {chunks_count} chunks from document '{document.title}'. Status: ready."
    except Exception as e:
        return f"Error: {str(e)}"

@mcp_server.tool()
async def get_voice_profile(api_key: str, client_id: str) -> str:
    """Get the voice profile for a client."""
    try:
        async with async_session_maker() as session:
            tenant = await get_mcp_tenant(api_key, session)
            client = await get_mcp_client(session, client_id, tenant)
            profile = await voice_profile_repo.get_voice_profile(session, client.id)
            if not profile:
                return "No voice profile set."
            
            banned_words_str = ", ".join(profile.banned_words) if profile.banned_words else "None"
            extra_instructions_str = profile.extra_instructions or "None"
            return f"Tone: {profile.tone}\nPOV: {profile.pov}\nBanned Words: {banned_words_str}\nExtra Instructions: {extra_instructions_str}"
    except Exception as e:
        return f"Error: {str(e)}"

@mcp_server.tool()
async def set_voice_profile(
    api_key: str, 
    client_id: str, 
    tone: Optional[str] = None, 
    pov: Optional[Literal["first_person", "second_person", "third_person"]] = None, 
    banned_words: Optional[List[str]] = None, 
    extra_instructions: Optional[str] = None
) -> str:
    """Set or update the voice profile for a client."""
    try:
        async with async_session_maker() as session:
            tenant = await get_mcp_tenant(api_key, session)
            client = await get_mcp_client(session, client_id, tenant)
            from src.schemas.voice_profile import VoiceProfileSet
            data = VoiceProfileSet(
                tone=tone,
                pov=pov,
                banned_words=banned_words or [],
                extra_instructions=extra_instructions
            )
            await voice_profile_repo.upsert_voice_profile(
                db=session,
                client_id=client.id,
                data=data
            )
            await session.commit()
            return f"Voice profile updated for client {client_id}."
    except Exception as e:
        return f"Error: {str(e)}"

@mcp_server.tool()
async def check_usage(api_key: str, client_id: str) -> str:
    """Check the LLM usage for a client."""
    try:
        async with async_session_maker() as session:
            tenant = await get_mcp_tenant(api_key, session)
            client = await get_mcp_client(session, client_id, tenant)
            byok = bool(client.llm_api_key_encrypted)
            return f"Usage this month: {client.usage_this_month} / {client.usage_cap} (BYOK: {byok})"
    except Exception as e:
        return f"Error: {str(e)}"
