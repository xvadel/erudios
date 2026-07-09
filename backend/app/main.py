from __future__ import annotations

import structlog
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from app.config import settings
from app.api.v1.router import api_router
from app.db.session import engine, AsyncSessionLocal
from app.db.base import Base
from app.core.exceptions import register_exception_handlers
from app.services.cache import cache_service
from app.core.logging import configure_logging
from app.core.middleware import RequestIDMiddleware

# Setup logging immediately
configure_logging(settings.APP_ENV)
log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle."""
    log.info("🚀 Starting Erudios backend", version=settings.APP_VERSION, env=settings.APP_ENV)

    # Validate at least one LLM provider is configured
    if not settings.available_llm_providers:
        raise RuntimeError(
            "No LLM provider configured. "
            "Set at least GEMINI_API_KEY or GROQ_API_KEY in your .env file."
        )
    log.info("✅ LLM providers active", providers=settings.available_llm_providers)

    # Connect to Redis
    await cache_service.connect()
    log.info("✅ Redis connected")

    # Seed database on first run
    if settings.AUTO_SEED_ON_STARTUP:
        from app.modules.topic_graph.seed_loader import seed_if_empty
        async with AsyncSessionLocal() as session:
            await seed_if_empty(session)

    log.info("✅ Startup complete — Erudios is ready")

    yield

    # Shutdown
    await cache_service.disconnect()
    await engine.dispose()
    log.info("👋 Erudios backend shutdown complete")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="AI Curriculum Builder — Personalized Learning for AI/ML Topics",
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        lifespan=lifespan,
    )

    # ── Middleware ────────────────────────────────────────────────────────────
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Exception handlers ────────────────────────────────────────────────────
    register_exception_handlers(app)

    # ── Prometheus Instrumentation ───────────────────────────────────────────
    Instrumentator().instrument(app).expose(app, endpoint="/metrics")

    # ── Routers ───────────────────────────────────────────────────────────────
    app.include_router(api_router, prefix="/api/v1")

    return app


app = create_app()
