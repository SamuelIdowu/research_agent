import base64
import hashlib
import secrets
from typing import List, Optional
from cryptography.fernet import Fernet, MultiFernet, InvalidToken

def _derive_fernet_key(secret: str) -> bytes:
    """Derives a 32-byte urlsafe base64 key from any given secret string."""
    derived_bytes = hashlib.sha256(secret.encode()).digest()
    return base64.urlsafe_b64encode(derived_bytes)

def get_multi_fernet(secret_or_secrets: Optional[str] = None) -> MultiFernet:
    """Creates a MultiFernet instance from one or more comma-separated secrets."""
    if not secret_or_secrets:
        from src.core.config import settings
        secret_or_secrets = getattr(settings, "ENCRYPTION_SECRET_KEY", None) or "default_secret_key_needs_override_32bytes"
    
    secrets_list = [s.strip() for s in secret_or_secrets.split(",") if s.strip()]
    if not secrets_list:
        raise ValueError("Encryption secret is not configured")
    
    fernets = [Fernet(_derive_fernet_key(s)) for s in secrets_list]
    return MultiFernet(fernets)

def hash_api_key(raw_key: str) -> str:
    """Hashes the raw API key for storage."""
    return hashlib.sha256(raw_key.encode()).hexdigest()

def generate_api_key() -> tuple[str, str]:
    """Generates a new API key. Returns (raw_key, hashed_key)."""
    raw_key = "ra_" + secrets.token_urlsafe(32)
    return raw_key, hash_api_key(raw_key)

def encrypt_byok_key(plaintext: str, secret: Optional[str] = None) -> str:
    """Encrypts a plaintext key using the primary key in the MultiFernet pool."""
    f = get_multi_fernet(secret)
    return f.encrypt(plaintext.encode()).decode()

def decrypt_byok_key(ciphertext: str, secret: Optional[str] = None) -> str:
    """Decrypts a ciphertext key using any valid key in the MultiFernet pool."""
    f = get_multi_fernet(secret)
    try:
        return f.decrypt(ciphertext.encode()).decode()
    except InvalidToken as e:
        raise ValueError("Decryption failed: invalid token or secret key") from e

