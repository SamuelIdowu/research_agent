import pytest
from unittest.mock import patch
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

@pytest.fixture(autouse=True)
def patch_mcp_session_maker(db_engine):
    test_session_maker = async_sessionmaker(
        db_engine, expire_on_commit=False, class_=AsyncSession
    )
    with patch("src.mcp.tools.async_session_maker", new=test_session_maker):
        yield

@pytest.fixture(autouse=True)
def mock_run_generation():
    with patch("src.services.generation.run_generation") as mock:
        mock.return_value = ("Draft content here.", [{"type": "kb", "excerpt": "Test"}])
        yield mock

@pytest.fixture(autouse=True)
def mock_embed_texts():
    with patch("src.services.ingestion.embed_texts") as mock:
        # returns 1 embedding of size 768 per chunk
        mock.side_effect = lambda chunks: [[0.1] * 768 for _ in chunks]
        yield mock
