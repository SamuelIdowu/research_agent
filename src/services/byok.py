from typing import Tuple, Optional
from cryptography.fernet import Fernet
from cryptography.fernet import InvalidToken

from src.models.client import Client
from src.core.config import settings

def encrypt_byok_key(raw_key: str, secret_key: Optional[str]) -> str:
    """Encrypts the raw API key using Fernet."""
    if not secret_key:
        raise ValueError("ENCRYPTION_SECRET_KEY is not configured")
    f = Fernet(secret_key.encode("utf-8"))
    return f.encrypt(raw_key.encode("utf-8")).decode("utf-8")

def decrypt_byok_key(ciphertext: str, secret_key: Optional[str]) -> str:
    """Decrypts the API key using Fernet."""
    if not secret_key:
        raise ValueError("ENCRYPTION_SECRET_KEY is not configured")
    f = Fernet(secret_key.encode("utf-8"))
    try:
        return f.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        raise ValueError("Failed to decrypt the BYOK key. The cipher or secret key may be invalid.")

def configure_byok(client: Client, provider: str, model: str, raw_key: str) -> Client:
    """Configures BYOK for a client and encrypts the key."""
    encrypted_key = encrypt_byok_key(raw_key, settings.ENCRYPTION_SECRET_KEY)
    client.llm_provider = provider
    client.llm_model = model
    client.llm_api_key_encrypted = encrypted_key
    return client

def get_decrypted_byok_key(client: Client) -> Optional[str]:
    """Retrieves and decrypts the client's BYOK key if available."""
    if client.llm_api_key_encrypted is None:
        return None
    return decrypt_byok_key(client.llm_api_key_encrypted, settings.ENCRYPTION_SECRET_KEY)

def resolve_model_for_client(client: Client) -> Tuple[str, Optional[str]]:
    """
    Returns (model_identifier, api_key_or_none) based on client config.
    Falls back to the default application model and key if the client has no BYOK.
    """
    decrypted_key = get_decrypted_byok_key(client)
    if decrypted_key and client.llm_model:
        return client.llm_model, decrypted_key
    return settings.DEFAULT_LLM_MODEL, None
