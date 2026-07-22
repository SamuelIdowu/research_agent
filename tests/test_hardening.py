import pytest
from httpx import AsyncClient
from src.main import app
from src.core.config import Settings
from src.api.dependencies import get_current_tenant
from src.models.tenant import Tenant
import uuid

@pytest.fixture(autouse=True)
def override_tenant():
    async def mock_tenant():
        return Tenant(id=uuid.uuid4(), name="Test Tenant")
    app.dependency_overrides[get_current_tenant] = mock_tenant
    yield
    app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_global_exception_handler():
    """Test that an unhandled exception returns a structured 500 JSON, not a traceback."""
    @app.get("/test-unhandled-error")
    async def unhandled_error():
        raise RuntimeError("Deliberate unhandled exception for testing")
    
    from httpx import ASGITransport
    async with AsyncClient(transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test") as client:
        response = await client.get("/test-unhandled-error")
        
    assert response.status_code == 500
    data = response.json()
    assert data["detail"] == "Internal server error"
    assert "request_id" in data
    assert data["type"] == "RuntimeError"

@pytest.mark.asyncio
async def test_request_id_in_response_header(async_client: AsyncClient):
    """Test that X-Request-ID is present in the response headers."""
    response = await async_client.get("/health")
    assert response.status_code == 200
    assert "x-request-id" in response.headers
    assert response.headers["x-request-id"] != "unknown"

@pytest.mark.asyncio
async def test_oversized_brief_rejected(async_client: AsyncClient):
    """Test that a brief exceeding the max length is rejected with 422."""
    oversized_brief = "a" * 5001
    payload = {
        "brief": oversized_brief,
        "client_id": str(uuid.uuid4())
    }
    response = await async_client.post("/generate", json=payload)
    assert response.status_code == 422
    data = response.json()
    assert "Invalid input at" in data["detail"]

@pytest.mark.asyncio
async def test_invalid_url_rejected(async_client: AsyncClient):
    """Test that an invalid URL is rejected with 422."""
    payload = {
        "source_type": "url",
        "url": "not-a-url",
        "client_id": str(uuid.uuid4())
    }
    response = await async_client.post("/documents", json=payload)
    assert response.status_code == 422

@pytest.mark.asyncio
async def test_invalid_uuid_path_param(async_client: AsyncClient):
    """Test that an invalid UUID in the path returns 422."""
    response = await async_client.get("/clients/not-a-uuid")
    assert response.status_code == 422
    assert "Invalid input at" in response.json()["detail"]

def test_startup_missing_encryption_key():
    """Test that application refuses to start if ENCRYPTION_SECRET_KEY is missing or too short."""
    with pytest.raises(ValueError, match="ENCRYPTION_SECRET_KEY must be set and at least 32 characters long"):
        Settings(
            POSTGRES_USER="test",
            POSTGRES_PASSWORD="test",
            POSTGRES_DB="test",
            POSTGRES_HOST="localhost",
            POSTGRES_PORT=5432,
            DATABASE_URL="postgresql+asyncpg://test:test@localhost/test",
            GEMINI_API_KEY="test_key",
            ENCRYPTION_SECRET_KEY="short"  # Too short
        )
