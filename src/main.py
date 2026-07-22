"""FastAPI application entrypoint."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Depends, Request
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.exceptions import RequestValidationError
import uuid
import time
import structlog

from src.db.session import engine
from src.core.logging import setup_logging
from src.api.middleware.error_handler import (
    global_exception_handler,
    http_exception_handler,
    validation_exception_handler
)
from src.api.routers.analytics import router as analytics_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: startup and shutdown events."""
    # Startup: configure logging
    setup_logging()
    
    yield
    # Shutdown: dispose of the connection pool
    await engine.dispose()


from src.api.routers import tenants, clients, documents, voice_profiles, generate, byok
from src.api.dependencies import get_current_tenant

from fastapi.openapi.utils import get_openapi

app = FastAPI(
    title="Research Agent",
    description="Pluggable Content Generation Agent — REST + MCP",
    version="0.1.0",
    lifespan=lifespan,
)

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    if "components" not in openapi_schema:
        openapi_schema["components"] = {}
    if "securitySchemes" not in openapi_schema["components"]:
        openapi_schema["components"]["securitySchemes"] = {
            "APIKeyHeader": {
                "type": "apiKey",
                "in": "header",
                "name": "X-Api-Key"
            }
        }
    for path in openapi_schema.get("paths", {}):
        if path != "/health":
            for method in openapi_schema["paths"][path]:
                openapi_schema["paths"][path][method]["security"] = [{"APIKeyHeader": []}]
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

app.add_exception_handler(Exception, global_exception_handler) # type: ignore
app.add_exception_handler(StarletteHTTPException, http_exception_handler) # type: ignore
app.add_exception_handler(RequestValidationError, validation_exception_handler) # type: ignore

@app.middleware("http")
async def add_request_context_middleware(request: Request, call_next):
    # Clear any leftover context
    structlog.contextvars.clear_contextvars()
    
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    
    # Bind context to structlog
    structlog.contextvars.bind_contextvars(
        request_id=request_id,
        method=request.method,
        path=request.url.path,
    )
    
    start_time = time.perf_counter()
    response = await call_next(request)
    process_time_ms = (time.perf_counter() - start_time) * 1000
    
    # We could log request completion here if desired, but for now we focus on context
    
    response.headers["X-Request-ID"] = request_id
    return response

app.include_router(tenants.public_router, prefix="/tenants")
app.include_router(tenants.router, prefix="/tenants", dependencies=[Depends(get_current_tenant)])
app.include_router(clients.router, prefix="/clients", dependencies=[Depends(get_current_tenant)])
app.include_router(voice_profiles.router, prefix="/clients", dependencies=[Depends(get_current_tenant)])
app.include_router(documents.router, prefix="/documents", dependencies=[Depends(get_current_tenant)])
app.include_router(generate.router, dependencies=[Depends(get_current_tenant)])
app.include_router(byok.router, prefix="/clients", dependencies=[Depends(get_current_tenant)])
app.include_router(analytics_router, prefix="/analytics", dependencies=[Depends(get_current_tenant)])

# Import tools to ensure they are registered with the mcp_server
import src.mcp.tools
from src.mcp.server import mcp_server
app.mount("/mcp", mcp_server.sse_app)  # type: ignore

@app.get("/health")
async def health_check() -> dict[str, str]:
    """Lightweight liveness probe."""
    return {"status": "ok"}
