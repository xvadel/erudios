from __future__ import annotations

import uuid
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
import structlog

log = structlog.get_logger()

class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware that assigns a unique X-Request-ID header to every incoming HTTP request
    and binds it to the current asynchronous context of structlog logger.
    """
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Get existing request ID from headers or generate a new one
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        
        # Bind the request ID to the current logging context
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)
        
        response = await call_next(request)
        
        # Add the request ID to response headers for downstream debugging
        response.headers["X-Request-ID"] = request_id
        return response
