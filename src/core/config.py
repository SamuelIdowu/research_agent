from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import model_validator
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment / .env file."""

    # Postgres connection details
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432

    # SQLAlchemy connection URLs
    DATABASE_URL: str  # async (asyncpg) — used by the app
    SYNC_DATABASE_URL: str = ""  # sync (psycopg) — used by Alembic

    # API keys
    GEMINI_API_KEY: Optional[str] = None
    TAVILY_API_KEY: Optional[str] = None

    # Security
    ENCRYPTION_SECRET_KEY: Optional[str] = None

    # OpenAI
    OPENAI_API_KEY: Optional[str] = None

    DEFAULT_LLM_MODEL: str = "gemini-3.5-flash"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @model_validator(mode='after')
    def validate_startup_config(self) -> 'Settings':
        if not self.ENCRYPTION_SECRET_KEY or len(self.ENCRYPTION_SECRET_KEY) < 32:
            raise ValueError("ENCRYPTION_SECRET_KEY must be set and at least 32 characters long.")
        if not self.GEMINI_API_KEY and not self.OPENAI_API_KEY:
            raise ValueError("At least one LLM API key (GEMINI_API_KEY or OPENAI_API_KEY) must be set.")
        if not self.DATABASE_URL.startswith("postgresql+asyncpg://"):
            raise ValueError("DATABASE_URL must start with 'postgresql+asyncpg://'")
        return self


settings = Settings()  # type: ignore[call-arg]
