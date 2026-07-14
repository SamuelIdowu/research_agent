"""FastAPI application entrypoint."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI

from src.db.session import engine


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: startup and shutdown events."""
    # Startup: nothing extra needed — engine is lazy
    yield
    # Shutdown: dispose of the connection pool
    await engine.dispose()


from src.api.routers import tenants, clients

app = FastAPI(
    title="Research Agent",
    description="Pluggable Content Generation Agent — REST + MCP",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(tenants.router, prefix="/tenants")
app.include_router(clients.router, prefix="/clients")


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Lightweight liveness probe."""
    return {"status": "ok"}
