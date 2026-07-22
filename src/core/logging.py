import logging
import sys
from typing import Any, Dict

import structlog
from structlog.types import EventDict

# We don't want to log secrets
SENSITIVE_KEYS = {"api_key", "llm_api_key_encrypted", "key"}

def drop_sensitive_keys(logger: logging.Logger, log_method: str, event_dict: EventDict) -> EventDict:
    """Remove sensitive keys from the event dict before logging."""
    keys_to_remove = []
    for k, v in event_dict.items():
        if any(sensitive in k.lower() for sensitive in SENSITIVE_KEYS):
            keys_to_remove.append(k)
        # Also drop full prompts if they are too long and passed explicitly
        if k == "prompt" and isinstance(v, str) and len(v) > 200:
            event_dict[k] = v[:200] + "... [TRUNCATED]"
            
    for k in keys_to_remove:
        event_dict.pop(k, None)
    return event_dict

def setup_logging(log_level: str = "INFO") -> None:
    """Configure structlog for JSON formatting."""
    
    # Configure the standard logging library to catch third-party logs
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper(), logging.INFO),
    )

    processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        drop_sensitive_keys,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer(),
    ]

    structlog.configure(
        processors=processors, # type: ignore
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
