"""FastAPI application entrypoint."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.db.session import engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown events."""
    # Startup: nothing extra needed — engine is lazy
    yield
    # Shutdown: dispose of the connection pool
    await engine.dispose()


app = FastAPI(
    title="Research Agent",
    description="Pluggable Content Generation Agent — REST + MCP",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health_check():
    """Lightweight liveness probe."""
    return {"status": "ok"}
