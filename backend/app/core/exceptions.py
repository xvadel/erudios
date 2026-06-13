from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
import structlog

log = structlog.get_logger()


class ErudiosError(Exception):
    """Base exception for all Erudios errors."""
    status_code: int = 500
    detail: str = "Internal server error"

    def __init__(self, detail: str | None = None):
        self.detail = detail or self.__class__.detail
        super().__init__(self.detail)


class NotFoundError(ErudiosError):
    status_code = 404
    detail = "Resource not found"


class UnauthorizedError(ErudiosError):
    status_code = 401
    detail = "Authentication required"


class ForbiddenError(ErudiosError):
    status_code = 403
    detail = "Access denied"


class ValidationError(ErudiosError):
    status_code = 422
    detail = "Validation error"


class ProviderExhaustedError(ErudiosError):
    status_code = 503
    detail = "All LLM providers are temporarily exhausted. Content is queued for generation."


class ConfigurationError(ErudiosError):
    status_code = 500
    detail = "Configuration error"


class ResourceDiscoveryError(ErudiosError):
    status_code = 502
    detail = "Resource discovery failed"


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ErudiosError)
    async def erudios_error_handler(request: Request, exc: ErudiosError) -> JSONResponse:
        log.warning("Application error", error=str(exc), path=request.url.path)
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.__class__.__name__, "detail": exc.detail},
        )

    @app.exception_handler(Exception)
    async def generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
        log.error("Unhandled exception", error=str(exc), path=request.url.path, exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": "InternalServerError", "detail": "An unexpected error occurred"},
        )
