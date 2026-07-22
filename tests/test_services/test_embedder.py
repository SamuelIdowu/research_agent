import pytest
from src.services.embedder import embed_texts
from src.core.config import settings

@pytest.mark.asyncio
async def test_embed_texts_empty():
    assert await embed_texts([]) == []

@pytest.mark.asyncio
async def test_embed_texts_test_mode():
    settings.DEFAULT_LLM_MODEL = "test"
    res = await embed_texts(["hello"])
    assert len(res) == 1
    assert len(res[0]) == 768
    assert res[0] == [0.0] * 768

@pytest.mark.asyncio
async def test_embed_texts_real_mock():
    # temporarily change model to not test
    old_model = settings.DEFAULT_LLM_MODEL
    settings.DEFAULT_LLM_MODEL = "gemini-1.5-flash"
    
    from unittest.mock import patch, MagicMock, AsyncMock
    with patch("src.services.embedder.default_gemini_client") as mock_client:
        mock_response = MagicMock()
        mock_data = MagicMock()
        mock_data.values = [0.1, 0.2, 0.3]
        mock_response.embeddings = [mock_data]
        
        mock_client.aio.models.embed_content = AsyncMock(return_value=mock_response)
        
        res = await embed_texts(["hello world"])
        assert len(res) == 1
        assert res[0] == [0.1, 0.2, 0.3]
        
    settings.DEFAULT_LLM_MODEL = old_model

@pytest.mark.asyncio
async def test_embed_texts_retry_logic():
    old_model = settings.DEFAULT_LLM_MODEL
    settings.DEFAULT_LLM_MODEL = "gemini-1.5-flash"
    
    from unittest.mock import patch, MagicMock, AsyncMock
    with patch("src.services.embedder.default_gemini_client") as mock_client, \
         patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        
        # Make it fail twice, then succeed
        mock_client.aio.models.embed_content = AsyncMock(side_effect=[
            Exception("Rate limit 1"),
            Exception("Rate limit 2"),
            MagicMock(embeddings=[MagicMock(values=[0.9])])
        ])
        
        res = await embed_texts(["hello retries"])
        assert len(res) == 1
        assert res[0] == [0.9]
        assert mock_client.aio.models.embed_content.call_count == 3
        assert mock_sleep.call_count == 2
        
    settings.DEFAULT_LLM_MODEL = old_model
