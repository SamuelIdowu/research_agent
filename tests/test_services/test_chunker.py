from unittest.mock import patch

import pytest
import httpx

from src.services.chunker import chunk_text, chunk_url

def test_chunk_text_basic():
    # ~1000 word text
    text = "word " * 1000
    chunks = chunk_text(text, chunk_size=500, chunk_overlap=50)
    assert len(chunks) > 1
    # Check that chunks are generated
    assert all(len(chunk) > 0 for chunk in chunks)

def test_chunk_overlap():
    text = "This is a simple test sentence that we will use to check overlap behavior. " * 50
    chunks = chunk_text(text, chunk_size=50, chunk_overlap=10)
    assert len(chunks) > 1
    assert len(chunks) > 2

def test_chunk_empty_string():
    assert chunk_text("") == []
    assert chunk_text(None) == []

@patch("src.services.chunker.httpx.get")
def test_chunk_url(mock_get):
    class MockResponse:
        def __init__(self):
            self.text = "<html><body><h1>Title</h1><p>Some text content.</p></body></html>"
            
        def raise_for_status(self):
            pass

    mock_get.return_value = MockResponse()
    
    chunks = chunk_url("http://example.com")
    assert len(chunks) == 1
    # Check that HTML is stripped and text remains
    assert "Title" in chunks[0]
    assert "Some text content." in chunks[0]
    assert "<html>" not in chunks[0]
    
@patch("src.services.chunker.httpx.get")
def test_chunk_url_failure(mock_get):
    mock_get.side_effect = httpx.RequestError("Network error")
    with pytest.raises(ValueError):
        chunk_url("http://example.com")
