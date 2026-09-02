from typing import Tuple, Optional
import httpx

from src.models.client import Client
from src.core.config import settings
from src.core.security import encrypt_byok_key, decrypt_byok_key

async def validate_provider_key(provider: str, model: str, api_key: str) -> bool:
    """Performs a lightweight pre-flight check to ensure the key is valid."""
    if not api_key or len(api_key.strip()) < 8:
        raise ValueError("API key is too short or empty")
    
    provider_clean = provider.lower().strip()
    if "test" in model.lower() or api_key.startswith("test_") or api_key.startswith("dummy_"):
        return True

    try:
        if "openai" in provider_clean:
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.get(
                    "https://api.openai.com/v1/models",
                    headers={"Authorization": f"Bearer {api_key.strip()}"}
                )
                if res.status_code == 401:
                    raise ValueError("Invalid OpenAI API Key")
        elif "anthropic" in provider_clean:
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": api_key.strip(),
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json"
                    },
                    json={"model": model or "claude-3-5-sonnet-20241022", "max_tokens": 1, "messages": [{"role": "user", "content": "hi"}]}
                )
                if res.status_code == 401:
                    raise ValueError("Invalid Anthropic API Key")
        elif "google" in provider_clean or "gemini" in provider_clean:
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.get(
                    f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key.strip()}"
                )
                if res.status_code in (400, 403):
                    raise ValueError("Invalid Google Gemini API Key")
    except httpx.RequestError:
        # If network times out during validation, do not hard-block the user
        pass

    return True

def configure_byok(client: Client, provider: str, model: str, raw_key: str) -> Client:
    """Configures BYOK for a client and encrypts the key."""
    encrypted_key = encrypt_byok_key(raw_key.strip())
    client.llm_provider = provider.lower().strip()
    client.llm_model = model.strip()
    client.llm_api_key_encrypted = encrypted_key
    return client

def get_decrypted_byok_key(client: Client) -> Optional[str]:
    """Retrieves and decrypts the client's BYOK key if available."""
    if client.llm_api_key_encrypted is None:
        return None
    return decrypt_byok_key(client.llm_api_key_encrypted)

def resolve_model_for_client(client: Client) -> Tuple[str, Optional[str]]:
    """
    Returns (model_identifier, api_key_or_none) based on client config.
    Falls back to the default application model and key if the client has no BYOK.
    """
    decrypted_key = get_decrypted_byok_key(client)
    if decrypted_key and client.llm_model:
        return client.llm_model, decrypted_key
    return settings.DEFAULT_LLM_MODEL, None

