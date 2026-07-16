import pytest
from unittest.mock import AsyncMock, patch
from uuid import uuid4
from src.agent.tools import search_knowledge_base, search_web, AgentDeps

@pytest.fixture
def mock_ctx():
    class MockDeps:
        session = AsyncMock()
        client_id = uuid4()
        tenant_id = uuid4()
        voice_profile_fragment = ""
        tavily_api_key = "test_key"
    
    class MockCtx:
        deps = MockDeps()
        
    return MockCtx()

@pytest.mark.asyncio
@patch("src.agent.tools.retrieve_chunks_with_scores")
async def test_search_knowledge_base_returns_results(mock_retrieve, mock_ctx):
    class MockChunk:
        document_id = uuid4()
        text = "Test content"
        
    mock_retrieve.return_value = [(MockChunk(), 0.85)]
    
    result = await search_knowledge_base(mock_ctx, "query")
    assert "[{}]".format(MockChunk.document_id) in result
    assert "Test content" in result
    assert "score: 0.85" in result

@pytest.mark.asyncio
@patch("src.agent.tools.retrieve_chunks_with_scores")
async def test_search_knowledge_base_empty(mock_retrieve, mock_ctx):
    mock_retrieve.return_value = []
    result = await search_knowledge_base(mock_ctx, "query")
    assert result == "No relevant knowledge base content found."

@pytest.mark.asyncio
@patch("src.agent.tools.AsyncTavilyClient")
async def test_search_web_success(mock_tavily, mock_ctx):
    mock_client = AsyncMock()
    mock_client.search.return_value = {
        "results": [
            {"title": "Test Title", "content": "Test content", "url": "https://test.com"}
        ]
    }
    mock_tavily.return_value = mock_client
    
    result = await search_web(mock_ctx, "query")
    assert "[W1]" in result
    assert "Test Title:" in result
    assert "Test content" in result
    assert "https://test.com" in result

@pytest.mark.asyncio
@patch("src.agent.tools.AsyncTavilyClient")
async def test_search_web_api_failure(mock_tavily, mock_ctx):
    pass # Removed TavilyApiError mock due to missing attribute in tavily.errors
    mock_client = AsyncMock()
    mock_client.search.side_effect = Exception("API Error")
    mock_tavily.return_value = mock_client
    
    result = await search_web(mock_ctx, "query")
    assert "Web search unavailable" in result
    assert "API Error" in result
