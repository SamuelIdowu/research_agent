import asyncio
import pytest
import pytest_asyncio
import sqlalchemy as sa
from typing import AsyncGenerator, Generator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession, AsyncEngine
from src.models.base import Base
import os

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", 
    "postgresql+asyncpg://postgres:postgres@localhost:5432/research_agent_test"
)


from sqlalchemy.pool import NullPool

@pytest_asyncio.fixture
async def db_engine() -> AsyncGenerator[AsyncEngine, None]:
    engine = create_async_engine(TEST_DATABASE_URL, echo=False, poolclass=NullPool)
    
    async with engine.begin() as conn:
        await conn.execute(sa.text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
        
    yield engine
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        
    await engine.dispose()

import src.models # Load all models
from src.main import app
from src.db.session import get_db

@pytest_asyncio.fixture
async def async_session(db_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    async_session_factory = async_sessionmaker(
        db_engine, expire_on_commit=False, class_=AsyncSession
    )
    async with async_session_factory() as session:
        yield session
        await session.rollback()

@pytest.fixture(autouse=True)
def override_get_db(async_session: AsyncSession) -> Generator[None, None, None]:
    async def _get_test_db() -> AsyncGenerator[AsyncSession, None]:
        yield async_session

    app.dependency_overrides[get_db] = _get_test_db
    yield
    app.dependency_overrides.clear()
