from pydantic_settings import BaseSettings, SettingsConfigDict
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

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
