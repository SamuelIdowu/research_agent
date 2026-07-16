import asyncio
from typing import Optional

from google import genai

from src.core.config import settings

# Global client
default_gemini_client = None
if settings.GEMINI_API_KEY:
    default_gemini_client = genai.Client(api_key=settings.GEMINI_API_KEY)


async def embed_texts(texts: list[str], client_api_key: Optional[str] = None) -> list[list[float]]:
    if not texts:
        return []
        
    if settings.DEFAULT_LLM_MODEL == "test":
        return [[0.0]*768 for _ in texts]

    client = default_gemini_client
    if client_api_key:
        client = genai.Client(api_key=client_api_key)
    
    if not client:
        raise ValueError("Gemini API key is missing. Please set it in config or pass client_api_key.")

    # Exponential backoff for rate limiting (max 3 retries)
    max_retries = 3
    base_delay = 1.0

    for attempt in range(max_retries + 1):
        try:
            response = await client.aio.models.embed_content(
                model="text-embedding-004",
                contents=texts
            )
            if response.embeddings:
                return [data.values for data in response.embeddings if data.values is not None]
            return []
        except Exception as e:
            if attempt == max_retries:
                raise e
            await asyncio.sleep(base_delay * (2 ** attempt))
            
    return [] # Should not be reached
