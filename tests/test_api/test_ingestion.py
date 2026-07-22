import pytest
from httpx import AsyncClient
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.models.document import Document
from src.models.document_chunk import DocumentChunk

@pytest.fixture
async def tenant(async_client: AsyncClient) -> dict[str, Any]:
    response = await async_client.post("/tenants", json={"name": "Ingestion Test Tenant"})
    return response.json()

@pytest.fixture
async def client_data(async_client: AsyncClient, tenant: dict[str, Any]) -> dict[str, Any]:
    response = await async_client.post("/clients", json={
        "tenant_id": tenant["id"],
        "name": "Ingestion Test Client"
    }, headers={"X-Api-Key": tenant["raw_api_key"]})
    return response.json()

@pytest.mark.asyncio
async def test_ingest_text_document(async_client: AsyncClient, tenant: dict[str, Any], client_data: dict[str, Any], async_session: AsyncSession):
    from unittest.mock import patch
    with patch("src.services.ingestion.embed_texts") as mock_embed:
        mock_embed.return_value = [[0.1] * 768]
        
        response = await async_client.post(
            "/documents",
            json={"client_id": client_data["id"], "source_type": "text", "content": "This is a test document."},
            headers={"X-Api-Key": tenant["raw_api_key"]}
        )
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "ready"
        assert data["client_id"] == client_data["id"]
        
        # Verify chunks created
        stmt = select(DocumentChunk).where(DocumentChunk.document_id == data["id"])
        chunks = (await async_session.execute(stmt)).scalars().all()
        assert len(chunks) > 0

@pytest.mark.asyncio
async def test_ingest_invalid_source_type(async_client: AsyncClient, tenant: dict[str, Any], client_data: dict[str, Any]):
    response = await async_client.post(
        "/documents",
        json={"client_id": client_data["id"], "source_type": "unknown", "content": "This is a test document."},
        headers={"X-Api-Key": tenant["raw_api_key"]}
    )
    assert response.status_code == 422

@pytest.mark.asyncio
async def test_list_documents(async_client: AsyncClient, tenant: dict[str, Any], client_data: dict[str, Any]):
    from unittest.mock import patch
    with patch("src.services.ingestion.embed_texts") as mock_embed:
        mock_embed.return_value = [[0.1] * 768]
        
        # Ingest one document first
        await async_client.post(
            "/documents",
            json={"client_id": client_data["id"], "source_type": "text", "content": "List test document."},
            headers={"X-Api-Key": tenant["raw_api_key"]}
        )

    response = await async_client.get(
        f"/documents?client_id={client_data['id']}",
        headers={"X-Api-Key": tenant["raw_api_key"]}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) >= 1
    assert data["total"] >= 1

@pytest.mark.asyncio
async def test_delete_document_cascades_chunks(async_client: AsyncClient, tenant: dict[str, Any], client_data: dict[str, Any], async_session: AsyncSession):
    from unittest.mock import patch
    with patch("src.services.ingestion.embed_texts") as mock_embed:
        mock_embed.return_value = [[0.1] * 768]
        
        # Ingest one document first
        post_resp = await async_client.post(
            "/documents",
            json={"client_id": client_data["id"], "source_type": "text", "content": "Delete test document."},
            headers={"X-Api-Key": tenant["raw_api_key"]}
        )
        doc_id = post_resp.json()["id"]

    response = await async_client.delete(
        f"/documents/{doc_id}?client_id={client_data['id']}",
        headers={"X-Api-Key": tenant["raw_api_key"]}
    )
    assert response.status_code == 204

    stmt = select(DocumentChunk).where(DocumentChunk.document_id == doc_id)
    chunks = (await async_session.execute(stmt)).scalars().all()
    assert len(chunks) == 0
