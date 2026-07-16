import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.tenant import Tenant
from src.models.client import Client
from src.models.document import Document
from src.models.document_chunk import DocumentChunk
from src.services.retrieval import retrieve_chunks
from httpx import AsyncClient

@pytest.fixture
async def sample_tenant(async_session: AsyncSession) -> Tenant:
    tenant = Tenant(name="Isolation Tenant")
    async_session.add(tenant)
    await async_session.commit()
    await async_session.refresh(tenant)
    return tenant

@pytest.fixture
async def alice_client(async_session: AsyncSession, sample_tenant: Tenant) -> Client:
    client = Client(name="Alice", tenant_id=sample_tenant.id)
    async_session.add(client)
    await async_session.commit()
    await async_session.refresh(client)
    return client

@pytest.fixture
async def bob_client(async_session: AsyncSession, sample_tenant: Tenant) -> Client:
    client = Client(name="Bob", tenant_id=sample_tenant.id)
    async_session.add(client)
    await async_session.commit()
    await async_session.refresh(client)
    return client

@pytest.mark.asyncio
async def test_client_isolation_zero_contamination(
    async_session: AsyncSession,
    alice_client: Client,
    bob_client: Client
):
    from unittest.mock import patch
    
    with patch("src.services.retrieval.embed_texts") as mock_embed:
        # Mock embedder: always returns a vector. Let's say all vectors are the same
        # to ensure pgvector finds both chunks as highly similar, thus relying 
        # ENTIRELY on the client_id filter to separate them.
        mock_embed.return_value = [[0.1] * 768]
        
        doc_alice = Document(client_id=alice_client.id, tenant_id=alice_client.tenant_id, source_type="text")
        doc_bob = Document(client_id=bob_client.id, tenant_id=bob_client.tenant_id, source_type="text")
        
        async_session.add_all([doc_alice, doc_bob])
        await async_session.commit()
        await async_session.refresh(doc_alice)
        await async_session.refresh(doc_bob)
        
        alice_chunk = DocumentChunk(document_id=doc_alice.id, client_id=alice_client.id, text="Alice's apples", embedding=[0.1]*768, chunk_index=0)
        bob_chunk = DocumentChunk(document_id=doc_bob.id, client_id=bob_client.id, text="Bob's oranges", embedding=[0.1]*768, chunk_index=0)
        
        async_session.add_all([alice_chunk, bob_chunk])
        await async_session.commit()
        
        # 1. Alice searches for apples
        alice_results = await retrieve_chunks(async_session, "apples", alice_client.id, top_k=5)
        assert len(alice_results) == 1
        assert alice_results[0].text == "Alice's apples"
        assert alice_results[0].client_id == alice_client.id
        
        # 2. Alice searches for oranges (Bob's info) -> should return nothing from Bob
        alice_oranges_results = await retrieve_chunks(async_session, "oranges", alice_client.id, top_k=5)
        assert len(alice_oranges_results) == 1
        assert alice_oranges_results[0].text == "Alice's apples" # Since embeddings are identical, it falls back to whatever Alice has
        assert alice_oranges_results[0].client_id == alice_client.id
        
        # 3. Bob searches for oranges
        bob_results = await retrieve_chunks(async_session, "oranges", bob_client.id, top_k=5)
        assert len(bob_results) == 1
        assert bob_results[0].text == "Bob's oranges"
        assert bob_results[0].client_id == bob_client.id
        
        # 4. Bob searches for apples (Alice's info) -> should return nothing from Alice
        bob_apples_results = await retrieve_chunks(async_session, "apples", bob_client.id, top_k=5)
        assert len(bob_apples_results) == 1
        assert bob_apples_results[0].text == "Bob's oranges"
        assert bob_apples_results[0].client_id == bob_client.id
