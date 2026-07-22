import uuid
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.exceptions import RequestValidationError
import structlog

logger = structlog.get_logger(__name__)

async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch all unhandled exceptions."""
    request_id = request.state.request_id if hasattr(request.state, "request_id") else "unknown"
    
    # Log the full traceback internally
    logger.error("unhandled_exception", exc_info=exc, path=request.url.path, type=exc.__class__.__name__)
    
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "request_id": request_id,
            "type": exc.__class__.__name__
        }
    )

async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Standardize all HTTP exceptions."""
    request_id = request.state.request_id if hasattr(request.state, "request_id") else "unknown"
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "status_code": exc.status_code,
            "request_id": request_id
        }
    )

async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle request validation errors nicely."""
    request_id = request.state.request_id if hasattr(request.state, "request_id") else "unknown"
    
    # Extract the first useful error message if possible
    errors = exc.errors()
    detail = "Validation error"
    if errors:
        first_error = errors[0]
        loc = ".".join(str(l) for l in first_error.get("loc", []))
        msg = first_error.get("msg", "")
        detail = f"Invalid input at '{loc}': {msg}"
    
    return JSONResponse(
        status_code=422,
        content={
            "detail": detail,
            "status_code": 422,
            "request_id": request_id,
            "details": errors
        }
    )
