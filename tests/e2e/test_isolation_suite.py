import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.tenant import Tenant
from src.models.client import Client
from src.models.document import Document
from src.models.document_chunk import DocumentChunk
from src.services.retrieval import retrieve_chunks

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
async def test_vector_isolation(
    async_session: AsyncSession,
    alice_client: Client,
    bob_client: Client
):
    from unittest.mock import patch
    
    with patch("src.services.retrieval.embed_texts") as mock_embed:
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
        
        # 2. Alice searches for oranges -> should return nothing from Bob
        alice_oranges_results = await retrieve_chunks(async_session, "oranges", alice_client.id, top_k=5)
        assert len(alice_oranges_results) == 1
        assert alice_oranges_results[0].text == "Alice's apples"

@pytest.mark.asyncio
async def test_cross_tenant_generation_request_access(async_client: AsyncClient):
    tenant_a_resp = await async_client.post("/tenants", json={"name": "Tenant A"})
    api_key_a = tenant_a_resp.json()["raw_api_key"]
    headers_a = {"X-Api-Key": api_key_a}
    
    tenant_b_resp = await async_client.post("/tenants", json={"name": "Tenant B"})
    api_key_b = tenant_b_resp.json()["raw_api_key"]
    headers_b = {"X-Api-Key": api_key_b}
    
    client_a_resp = await async_client.post("/clients", json={"name": "Client A", "usage_cap": 10}, headers=headers_a)
    client_a_id = client_a_resp.json()["id"]
    
    # We must mock completion call or just see the request being created
    # Wait, /generate requires documents? No, it just generates.
    from unittest.mock import patch
    with patch("src.services.generation.run_generation") as mock_run_gen:
        mock_run_gen.return_value = ("Generated", [{"type": "kb", "title": "test", "url": "test", "excerpt": "test"}], 100, 50)
        
        generate_resp = await async_client.post(
            "/generate", 
            json={"client_id": client_a_id, "brief": "Hi"}, 
            headers=headers_a
        )
        assert generate_resp.status_code == 200
        request_id = generate_resp.json()["request_id"]
    
    # B tries to get A's generation
    get_gen_b = await async_client.get(f"/generations/{request_id}", headers=headers_b)
    assert get_gen_b.status_code == 404

@pytest.mark.asyncio
async def test_cross_tenant_client_access(async_client: AsyncClient):
    tenant_a_resp = await async_client.post("/tenants", json={"name": "Tenant A"})
    headers_a = {"X-Api-Key": tenant_a_resp.json()['raw_api_key']}
    
    tenant_b_resp = await async_client.post("/tenants", json={"name": "Tenant B"})
    headers_b = {"X-Api-Key": tenant_b_resp.json()['raw_api_key']}
    
    client_a_resp = await async_client.post("/clients", json={"name": "Client X"}, headers=headers_a)
    client_x_id = client_a_resp.json()["id"]
    
    get_client_b = await async_client.get(f"/clients/{client_x_id}", headers=headers_b)
    assert get_client_b.status_code == 404

@pytest.mark.asyncio
async def test_cross_tenant_document_access(async_client: AsyncClient):
    tenant_a_resp = await async_client.post("/tenants", json={"name": "Tenant A"})
    headers_a = {"X-Api-Key": tenant_a_resp.json()['raw_api_key']}
    
    tenant_b_resp = await async_client.post("/tenants", json={"name": "Tenant B"})
    headers_b = {"X-Api-Key": tenant_b_resp.json()['raw_api_key']}
    
    client_a_resp = await async_client.post("/clients", json={"name": "Client X"}, headers=headers_a)
    client_x_id = client_a_resp.json()["id"]
    
    doc_a_resp = await async_client.post("/documents", json={"client_id": client_x_id, "source_type": "text", "content": "Test doc", "title": "Doc"}, headers=headers_a)
    doc_a_id = doc_a_resp.json()["id"]
    
    get_doc_b = await async_client.get(f"/documents/{doc_a_id}?client_id={client_x_id}", headers=headers_b)
    assert get_doc_b.status_code == 404

@pytest.mark.asyncio
async def test_cross_client_vector_query(async_client: AsyncClient):
    # This overlaps with test_vector_isolation but tests the API layer instead.
    # We will test retrieval during /generate by mocking the LLM but not retrieval.
    tenant_a_resp = await async_client.post("/tenants", json={"name": "Tenant A"})
    headers_a = {"X-Api-Key": tenant_a_resp.json()['raw_api_key']}
    
    client_y_resp = await async_client.post("/clients", json={"name": "Client Y"}, headers=headers_a)
    client_y_id = client_y_resp.json()["id"]
    
    client_z_resp = await async_client.post("/clients", json={"name": "Client Z"}, headers=headers_a)
    client_z_id = client_z_resp.json()["id"]
    
    # Ingest content for Y and Z
    await async_client.post("/documents", json={"client_id": client_y_id, "source_type": "text", "content": "Y-specific content", "title": "Doc"}, headers=headers_a)
    await async_client.post("/documents", json={"client_id": client_z_id, "source_type": "text", "content": "Z-specific content", "title": "Doc"}, headers=headers_a)
    
    # generate calls run_generation internally. We can just mock run_generation 
    # and assert that the dependencies passed have the correct client_id.
    from unittest.mock import patch
    with patch("src.services.generation.run_generation") as mock_run_gen:
        mock_run_gen.return_value = ("Generated", [{"type": "kb", "title": "test", "url": "test", "excerpt": "test"}], 100, 50)
        
        gen_y_resp = await async_client.post(
            "/generate", 
            json={"client_id": client_y_id, "brief": "Tell me about Z-specific"}, 
            headers=headers_a
        )
        assert gen_y_resp.status_code == 200
        args, kwargs = mock_run_gen.call_args
        deps = args[0]
        assert str(deps.client_id) == client_y_id
            
        gen_z_resp = await async_client.post(
            "/generate", 
            json={"client_id": client_z_id, "brief": "Tell me about Y-specific"}, 
            headers=headers_a
        )
        assert gen_z_resp.status_code == 200
        args, kwargs = mock_run_gen.call_args
        deps = args[0]
        assert str(deps.client_id) == client_z_id
