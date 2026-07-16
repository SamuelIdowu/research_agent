import httpx
from langchain_text_splitters import RecursiveCharacterTextSplitter
import markdownify

def chunk_text(text: str, chunk_size: int = 500, chunk_overlap: int = 50) -> list[str]:
    if not text:
        return []
    
    splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        model_name="text-embedding-3-small",
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    chunks = splitter.split_text(text)
    return chunks

def chunk_url(url: str) -> list[str]:
    try:
        response = httpx.get(url, follow_redirects=True, timeout=10.0)
        response.raise_for_status()
    except Exception as e:
        raise ValueError(f"Failed to fetch URL {url}: {e}")
    
    text = markdownify.markdownify(response.text, heading_style="ATX")
    return chunk_text(text)
