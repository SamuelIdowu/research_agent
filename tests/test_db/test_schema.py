import pytest
from typing import Any
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from src.models import Tenant, Client, Document, DocumentChunk, VoiceProfile

@pytest.mark.asyncio
async def test_all_tables_exist(async_session: Any) -> None:
    result = await async_session.execute(text(
        "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';"
    ))
    tables = [row[0] for row in result.fetchall()]
    
    expected_tables = {
        "tenants", "clients", "api_keys", "documents", 
        "document_chunks", "voice_profiles", "generation_requests"
    }
    
    assert expected_tables.issubset(set(tables))

@pytest.mark.asyncio
async def test_tenant_client_fk(async_session: Any) -> None:
    import uuid
    client = Client(name="Test Client", tenant_id=uuid.uuid4())
    async_session.add(client)
    with pytest.raises(IntegrityError):
        await async_session.commit()

@pytest.mark.asyncio
async def test_client_document_fk(async_session: Any) -> None:
    import uuid
    doc = Document(client_id=uuid.uuid4(), tenant_id=uuid.uuid4(), source_type="text")
    async_session.add(doc)
    with pytest.raises(IntegrityError):
        await async_session.commit()

@pytest.mark.asyncio
async def test_document_chunk_has_vector_column(async_session: Any) -> None:
    result = await async_session.execute(text(
        "SELECT data_type, udt_name FROM information_schema.columns "
        "WHERE table_name = 'document_chunks' AND column_name = 'embedding';"
    ))
    row = result.fetchone()
    assert row is not None
    assert row[0] == 'USER-DEFINED'
    assert row[1] == 'vector'

@pytest.mark.asyncio
async def test_voice_profile_unique_per_client(async_session: Any) -> None:
    tenant = Tenant(name="Test Tenant", api_key_hash="hash123")
    async_session.add(tenant)
    await async_session.commit()
    
    client = Client(name="Test Client", tenant_id=tenant.id)
    async_session.add(client)
    await async_session.commit()
    
    vp1 = VoiceProfile(client_id=client.id, tone="friendly")
    async_session.add(vp1)
    await async_session.commit()
    
    vp2 = VoiceProfile(client_id=client.id, tone="professional")
    async_session.add(vp2)
    with pytest.raises(IntegrityError):
        await async_session.commit()

@pytest.mark.asyncio
async def test_cascade_delete_client(async_session: Any) -> None:
    tenant = Tenant(name="Test Tenant 2", api_key_hash="hash456")
    async_session.add(tenant)
    await async_session.commit()
    
    client = Client(name="Test Client 2", tenant_id=tenant.id)
    async_session.add(client)
    await async_session.commit()
    
    doc = Document(client_id=client.id, tenant_id=tenant.id, source_type="text")
    async_session.add(doc)
    await async_session.commit()
    
    chunk = DocumentChunk(
        document_id=doc.id, 
        client_id=client.id, 
        text="Sample text", 
        embedding=[0.0]*1536,
        chunk_index=0
    )
    async_session.add(chunk)
    await async_session.commit()
    
    await async_session.delete(client)
    await async_session.commit()
    
    result_doc = await async_session.get(Document, doc.id)
    assert result_doc is None
    
    result_chunk = await async_session.get(DocumentChunk, chunk.id)
    assert result_chunk is None
