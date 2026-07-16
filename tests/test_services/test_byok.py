import pytest
from cryptography.fernet import Fernet
import uuid

from src.models.client import Client
from src.core.config import settings
from src.services import byok

# Setup dummy key for testing
settings.ENCRYPTION_SECRET_KEY = Fernet.generate_key().decode("utf-8")

def test_encrypt_decrypt_roundtrip():
    raw_key = "sk-secret123"
    encrypted = byok.encrypt_byok_key(raw_key, settings.ENCRYPTION_SECRET_KEY)
    assert encrypted != raw_key
    assert encrypted.startswith("gAAAAA")
    
    decrypted = byok.decrypt_byok_key(encrypted, settings.ENCRYPTION_SECRET_KEY)
    assert decrypted == raw_key

def test_decryption_failure_raises():
    bad_cipher = "gAAAAA_invalid_data_here"
    with pytest.raises(ValueError, match="Failed to decrypt"):
        byok.decrypt_byok_key(bad_cipher, settings.ENCRYPTION_SECRET_KEY)

def test_resolve_byok_client():
    client = Client(id=uuid.uuid4())
    byok.configure_byok(client, "openai", "gpt-4o", "sk-custom-key")
    
    model_id, key = byok.resolve_model_for_client(client)
    assert model_id == "gpt-4o"
    assert key == "sk-custom-key"

def test_resolve_default_client():
    client = Client(id=uuid.uuid4(), llm_model=None, llm_api_key_encrypted=None)
    model_id, key = byok.resolve_model_for_client(client)
    
    assert model_id == settings.DEFAULT_LLM_MODEL
    assert key is None
