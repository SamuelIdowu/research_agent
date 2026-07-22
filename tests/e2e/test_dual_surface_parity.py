import pytest
from httpx import AsyncClient
from unittest.mock import patch
import json
import base64

@pytest.mark.asyncio
async def test_generate_rest_vs_mcp_status_parity(async_client: AsyncClient, async_session):
    tenant_resp = await async_client.post("/tenants", json={"name": "Parity Tenant"})
    api_key = tenant_resp.json()["raw_api_key"]
    headers = {"X-Api-Key": api_key}

    client_resp = await async_client.post("/clients", json={"name": "Parity User", "usage_cap": 50}, headers=headers)
    client_id = client_resp.json()["id"]

    # Generate via REST
    with patch("src.services.generation.run_generation") as mock_run_gen:
        mock_run_gen.return_value = ("Generated REST", [{"type": "kb", "title": "test", "url": "test", "excerpt": "test"}], 100, 50)
        
        generate_resp = await async_client.post(
            "/generate", 
            json={"client_id": client_id, "brief": "Test parity"}, 
            headers=headers
        )
        assert generate_resp.status_code == 200
        assert generate_resp.json()["status"] == "completed"
        assert generate_resp.json()["draft"] == "Generated REST"

    from src.services.generation import generate_content
    from src.repositories import client_repo
    from src.models.tenant import Tenant
    from src.models.client import Client
    import uuid
    
    client_obj = await client_repo.get_client_by_id(async_session, uuid.UUID(client_id), uuid.UUID(tenant_resp.json()["id"]))
    if not client_obj:
        client_obj = Client(id=uuid.UUID(client_id), tenant_id=uuid.UUID(tenant_resp.json()["id"]))
        
    tenant_obj = Tenant(id=uuid.UUID(tenant_resp.json()["id"]), name="Parity Tenant")
    
    with patch("src.services.generation.run_generation") as mock_run_gen_mcp:
        mock_run_gen_mcp.return_value = ("Generated MCP", [{"type": "kb", "title": "test", "url": "test", "excerpt": "test"}], 100, 50)
        
        result = await generate_content(async_session, client_obj, tenant_obj, "Test parity MCP")
        assert result.status == "completed"
        assert result.output == "Generated MCP"

@pytest.mark.asyncio
async def test_ingest_rest_vs_mcp_chunk_count_parity(async_client: AsyncClient, async_session):
    # Just an integration verification that ingest gives the same chunks
    tenant_resp = await async_client.post("/tenants", json={"name": "Ingest Parity"})
    headers = {"X-Api-Key": tenant_resp.json()['raw_api_key']}

    client_resp = await async_client.post("/clients", json={"name": "Ingest User", "usage_cap": 50}, headers=headers)
    client_id = client_resp.json()["id"]

    text_to_ingest = "Parity check text " * 50

    # REST Ingest
    rest_doc_resp = await async_client.post(
        "/documents", 
        json={"client_id": client_id, "source_type": "text", "content": text_to_ingest, "title": "Doc"}, 
        headers=headers
    )
    assert rest_doc_resp.status_code == 201
    rest_doc_id = rest_doc_resp.json()["id"]

    # MCP Ingest parity - we just use the underlying service
    from src.repositories import document_repo
    from src.services.ingestion import ingest_document
    from sqlalchemy import select, func
    import uuid
    
    # Get chunks for REST
    rest_stmt = select(func.count()).select_from(document_repo.Document.chunks.property.mapper.class_).where(document_repo.Document.chunks.property.mapper.class_.document_id == uuid.UUID(rest_doc_id))
    n_chunks_rest = await async_session.scalar(rest_stmt)

    # Do MCP ingest
    doc = await document_repo.create_document(async_session, uuid.UUID(client_id), uuid.UUID(tenant_resp.json()["id"]), "text", title="Doc", source_url=None)
    await ingest_document(async_session, doc.id, uuid.UUID(client_id), "text", content=text_to_ingest, url=None)
    
    # Get chunks for MCP
    mcp_stmt = select(func.count()).select_from(document_repo.Document.chunks.property.mapper.class_).where(document_repo.Document.chunks.property.mapper.class_.document_id == doc.id)
    n_chunks_mcp = await async_session.scalar(mcp_stmt)
    
    assert n_chunks_rest == n_chunks_mcp

@pytest.mark.asyncio
async def test_voice_profile_rest_vs_mcp_parity(async_client: AsyncClient, async_session):
    tenant_resp = await async_client.post("/tenants", json={"name": "Voice Parity"})
    headers = {"X-Api-Key": tenant_resp.json()['raw_api_key']}

    client_resp = await async_client.post("/clients", json={"name": "Voice User", "usage_cap": 50}, headers=headers)
    client_id = client_resp.json()["id"]

    # Set via REST
    await async_client.put(
        f"/clients/{client_id}/voice_profile", 
        json={"tone": "authoritative", "pov": "third_person"},
        headers=headers
    )
    
    # Verify via service (simulating MCP read)
    from src.repositories import voice_profile_repo
    from src.schemas.voice_profile import VoiceProfileSet
    import uuid
    
    profile = await voice_profile_repo.get_voice_profile(async_session, uuid.UUID(client_id))
    assert profile is not None
    assert profile.tone == "authoritative"
    assert profile.pov == "third_person"

    # Set via service (simulating MCP write)
    await voice_profile_repo.upsert_voice_profile(async_session, uuid.UUID(client_id), VoiceProfileSet(tone="casual", pov="first_person", banned_words=[], extra_instructions=None))
    await async_session.commit()
    async_session.expire_all()

    # Verify via REST
    rest_get_vp = await async_client.get(f"/clients/{client_id}/voice_profile", headers=headers)
    assert rest_get_vp.json()["tone"] == "casual"
    assert rest_get_vp.json()["pov"] == "first_person"
