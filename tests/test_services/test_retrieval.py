import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.tenant import Tenant
from src.models.client import Client
from src.models.document import Document
from src.models.document_chunk import DocumentChunk
from src.services.retrieval import retrieve_chunks

@pytest.fixture
async def sample_tenant(async_session: AsyncSession) -> Tenant:
    tenant = Tenant(name="Test Tenant")
    async_session.add(tenant)
    await async_session.commit()
    await async_session.refresh(tenant)
    return tenant

@pytest.fixture
async def sample_client(async_session: AsyncSession, sample_tenant: Tenant) -> Client:
    client = Client(name="Test Client", tenant_id=sample_tenant.id)
    async_session.add(client)
    await async_session.commit()
    await async_session.refresh(client)
    return client

@pytest.mark.asyncio
async def test_retrieval_returns_correct_client_chunks(async_session: AsyncSession, sample_client: Client):
    from unittest.mock import patch
    with patch("src.services.retrieval.embed_texts") as mock_embed:
        mock_embed.return_value = [[0.1] * 768]
        
        doc = Document(client_id=sample_client.id, tenant_id=sample_client.tenant_id, source_type="text")
        async_session.add(doc)
        await async_session.commit()
        await async_session.refresh(doc)
        
        chunk = DocumentChunk(
            document_id=doc.id,
            client_id=sample_client.id,
            text="This is a test document",
            embedding=[0.1]*768,
            chunk_index=0
        )
        async_session.add(chunk)
        await async_session.commit()
        
        results = await retrieve_chunks(async_session, "test", sample_client.id)
        assert len(results) == 1
        assert results[0].text == "This is a test document"

@pytest.mark.asyncio
async def test_retrieval_top_k(async_session: AsyncSession, sample_client: Client):
    from unittest.mock import patch
    with patch("src.services.retrieval.embed_texts") as mock_embed:
        mock_embed.return_value = [[0.1] * 768]
        
        doc = Document(client_id=sample_client.id, tenant_id=sample_client.tenant_id, source_type="text")
        async_session.add(doc)
        await async_session.commit()
        await async_session.refresh(doc)
        
        chunks = [
            DocumentChunk(
                document_id=doc.id,
                client_id=sample_client.id,
                text=f"Chunk {i}",
                embedding=[0.1]*768,
                chunk_index=i
            ) for i in range(5)
        ]
        async_session.add_all(chunks)
        await async_session.commit()
        
        results = await retrieve_chunks(async_session, "test", sample_client.id, top_k=3)
        assert len(results) == 3

@pytest.mark.asyncio
async def test_retrieval_empty_kb(async_session: AsyncSession, sample_client: Client):
    from unittest.mock import patch
    with patch("src.services.retrieval.embed_texts") as mock_embed:
        mock_embed.return_value = [[0.1] * 768]
        results = await retrieve_chunks(async_session, "test", sample_client.id)
        assert len(results) == 0

@pytest.mark.asyncio
async def test_retrieval_with_scores(async_session: AsyncSession, sample_client: Client):
    from unittest.mock import patch
    from src.services.retrieval import retrieve_chunks_with_scores
    with patch("src.services.retrieval.embed_texts") as mock_embed:
        mock_embed.return_value = [[0.1] * 768]
        
        doc = Document(client_id=sample_client.id, tenant_id=sample_client.tenant_id, source_type="text")
        async_session.add(doc)
        await async_session.commit()
        await async_session.refresh(doc)
        
        chunk = DocumentChunk(
            document_id=doc.id,
            client_id=sample_client.id,
            text="This is a test document",
            embedding=[0.1]*768,
            chunk_index=0
        )
        async_session.add(chunk)
        await async_session.commit()
        
        results = await retrieve_chunks_with_scores(async_session, "test", sample_client.id)
        assert len(results) == 1
        # Check that we get a tuple of (DocumentChunk, score)
        chunk_res, score = results[0]
        assert chunk_res.text == "This is a test document"
        assert isinstance(score, float)
