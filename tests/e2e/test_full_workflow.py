import pytest
from httpx import AsyncClient
from unittest.mock import patch

@pytest.mark.asyncio
async def test_complete_developer_workflow(async_client: AsyncClient):
    # 1. Provision: POST /tenants -> save raw_api_key
    tenant_resp = await async_client.post("/tenants", json={"name": "E2E Full Workflow Tenant"})
    assert tenant_resp.status_code == 201
    tenant_data = tenant_resp.json()
    api_key = tenant_data["raw_api_key"]
    headers = {"X-Api-Key": api_key}

    # 2. Create client: POST /clients with usage_cap=50
    client_resp = await async_client.post("/clients", json={"name": "Museflow User", "usage_cap": 50}, headers=headers)
    assert client_resp.status_code == 201
    client_data = client_resp.json()
    client_id = client_data["id"]

    # 3. Ingest: POST /documents with sample brand text
    doc_resp = await async_client.post(
        "/documents", 
        json={"client_id": client_id, "source_type": "text", "content": "Museflow is an AI tool for rapid music prototyping and creative expression.", "title": "Doc"}, 
        headers=headers
    )
    assert doc_resp.status_code == 201
    
    # 4. Set voice: PUT /clients/{id}/voice-profile
    voice_resp = await async_client.put(
        f"/clients/{client_id}/voice_profile", 
        json={"tone": "casual", "pov": "first_person", "brand_keywords": ["Museflow", "music", "creative"]},
        headers=headers
    )
    assert voice_resp.status_code == 200

    # 5. Generate: POST /generate -> assert 200
    with patch("src.services.generation.run_generation") as mock_run_gen:
        mock_run_gen.return_value = ("Generated text", [{"type": "kb", "title": "test", "url": "test", "excerpt": "test"}], 100, 50)
        
        generate_resp = await async_client.post(
            "/generate", 
            json={"client_id": client_id, "brief": "Write a tweet about Museflow"}, 
            headers=headers
        )
        assert generate_resp.status_code == 200
        gen_data = generate_resp.json()
        assert gen_data["status"] == "completed"
        assert gen_data["draft"] == "Generated text"
        assert len(gen_data["sources"]) > 0
        
        # 6. Verify citation: at least one source has type="kb"
        has_kb_source = any(source.get("type") == "kb" for source in gen_data["sources"])
        assert has_kb_source, "No knowledge base sources cited"
        
        request_id = gen_data["request_id"]

    # 7. Retrieve: GET /generations/{request_id}
    get_gen_resp = await async_client.get(f"/generations/{request_id}", headers=headers)
    assert get_gen_resp.status_code == 200
    assert get_gen_resp.json()["draft"] == "Generated text"

    # 8. List generations: GET /clients/{id}/generations -> assert 1 item
    list_gen_resp = await async_client.get(f"/clients/{client_id}/generations", headers=headers)
    assert list_gen_resp.status_code == 200
    assert len(list_gen_resp.json()["items"]) == 1

    # 9. Assert usage incremented: GET /clients/{id} -> assert usage_this_month == 1
    get_client_resp = await async_client.get(f"/clients/{client_id}", headers=headers)
    assert get_client_resp.status_code == 200
    assert get_client_resp.json()["usage_this_month"] == 1

@pytest.mark.asyncio
async def test_streaming_workflow(async_client: AsyncClient):
    tenant_resp = await async_client.post("/tenants", json={"name": "Streaming Tenant"})
    api_key = tenant_resp.json()["raw_api_key"]
    headers = {"X-Api-Key": api_key}

    client_resp = await async_client.post("/clients", json={"name": "Streamer", "usage_cap": 5}, headers=headers)
    client_id = client_resp.json()["id"]

    await async_client.post("/documents", json={"client_id": client_id, "source_type": "text", "content": "Stream test text.", "title": "Doc"}, headers=headers)

    from httpx import AsyncClient as HttpxAsyncClient
    
    # generate streaming call
    with patch("src.services.streaming.generate_stream") as mock_stream_gen:
        # We need to simulate the async generator returned by `generate_stream` when stream=True
        async def mock_stream(*args, **kwargs):
            yield '0:"Hello "\n'
            yield '0:"World"\n'
            yield '8:[{"type": "kb", "title": "test", "url": "test", "excerpt": "test"}]\n'
            yield 'd:{"finishReason":"stop"}\n'

        mock_stream_gen.side_effect = mock_stream
        
        # Need to capture the streaming response properly
        # Test client from httpx doesn't support Server-Sent Events natively easily,
        # but we can read the raw bytes.
        async with async_client.stream("POST", "/generate?stream=true", json={"client_id": client_id, "brief": "stream me"}, headers=headers) as response:
            assert response.status_code == 200
            content = await response.aread()
            content_str = content.decode("utf-8")
            
            # Verify we got some chunk output
            assert "Hello" in content_str
            assert "World" in content_str
            
            request_id = response.headers.get("x-generation-id")
            assert request_id is not None
                
            # Check status updated to completed
            get_gen_resp = await async_client.get(f"/generations/{request_id}", headers=headers)
            assert get_gen_resp.status_code == 200
            assert get_gen_resp.json()["status"] == "completed"

@pytest.mark.asyncio
async def test_usage_cap_rate_limiting(async_client: AsyncClient):
    tenant_resp = await async_client.post("/tenants", json={"name": "Rate Limit Tenant"})
    api_key = tenant_resp.json()["raw_api_key"]
    headers = {"X-Api-Key": api_key}

    # Usage cap = 1
    client_resp = await async_client.post("/clients", json={"name": "Limited User", "usage_cap": 1}, headers=headers)
    client_id = client_resp.json()["id"]

    await async_client.post("/documents", json={"client_id": client_id, "source_type": "text", "content": "Something to retrieve.", "title": "Doc"}, headers=headers)

    with patch("src.services.generation.run_generation") as mock_run_gen:
        mock_run_gen.return_value = ("Gen", [{"type": "kb", "title": "test", "url": "test", "excerpt": "test"}], 100, 50)
        
        # 1st Request - should succeed
        generate_resp1 = await async_client.post(
            "/generate", 
            json={"client_id": client_id, "brief": "One"}, 
            headers=headers
        )
        assert generate_resp1.status_code == 200
        
        # 2nd Request - should fail with 402 or 429
        generate_resp2 = await async_client.post(
            "/generate", 
            json={"client_id": client_id, "brief": "Two"}, 
            headers=headers
        )
        assert generate_resp2.status_code == 429 # Using 429 Too Many Requests for usage cap
