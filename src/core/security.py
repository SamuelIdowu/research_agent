import base64
import hashlib
import secrets
from cryptography.fernet import Fernet

def get_fernet(secret: str) -> Fernet:
    """Derives a 32-byte Fernet key from the given secret."""
    if not secret:
        raise ValueError("Encryption secret is not configured")
    # Derive a 32-byte urlsafe base64 key using sha256
    derived_key = hashlib.sha256(secret.encode()).digest()
    b64_key = base64.urlsafe_b64encode(derived_key)
    return Fernet(b64_key)

def hash_api_key(raw_key: str) -> str:
    """Hashes the raw API key for storage."""
    return hashlib.sha256(raw_key.encode()).hexdigest()

def generate_api_key() -> tuple[str, str]:
    """Generates a new API key. Returns (raw_key, hashed_key)."""
    raw_key = "ra_" + secrets.token_urlsafe(32)
    return raw_key, hash_api_key(raw_key)

def encrypt_byok_key(plaintext: str, secret: str) -> str:
    """Encrypts a plaintext key using the provided secret."""
    f = get_fernet(secret)
    return f.encrypt(plaintext.encode()).decode()

def decrypt_byok_key(ciphertext: str, secret: str) -> str:
    """Decrypts a ciphertext key using the provided secret."""
    f = get_fernet(secret)
    try:
        return f.decrypt(ciphertext.encode()).decode()
    except Exception as e:
        raise ValueError("Decryption failed") from e
