"""FastAPI application entrypoint."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Depends

from src.db.session import engine


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: startup and shutdown events."""
    # Startup: nothing extra needed — engine is lazy
    yield
    # Shutdown: dispose of the connection pool
    await engine.dispose()


from src.api.routers import tenants, clients, documents, voice_profiles, generate, byok
from src.api.dependencies import get_current_tenant

app = FastAPI(
    title="Research Agent",
    description="Pluggable Content Generation Agent — REST + MCP",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(tenants.public_router, prefix="/tenants")
app.include_router(tenants.router, prefix="/tenants", dependencies=[Depends(get_current_tenant)])
app.include_router(clients.router, prefix="/clients", dependencies=[Depends(get_current_tenant)])
app.include_router(voice_profiles.router, prefix="/clients", dependencies=[Depends(get_current_tenant)])
app.include_router(documents.router, prefix="/documents", dependencies=[Depends(get_current_tenant)])
app.include_router(generate.router, dependencies=[Depends(get_current_tenant)])
app.include_router(byok.router, prefix="/clients", dependencies=[Depends(get_current_tenant)])

# Import tools to ensure they are registered with the mcp_server
import src.mcp.tools
from src.mcp.server import mcp_server
app.mount("/mcp", mcp_server.sse_app)  # type: ignore

@app.get("/health")
async def health_check() -> dict[str, str]:
    """Lightweight liveness probe."""
    return {"status": "ok"}
