from __future__ import annotations

import json
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.content import GeneratedContent
from app.services.cache import cache_service
from app.config import settings

log = structlog.get_logger()


class ContentCacheService:
    """
    Two-layer shared content cache:
    - L1: Redis (hot, 24h TTL) — fast lookups
    - L2: PostgreSQL GeneratedContent table (permanent) — shared across users

    Cache keys format: "{topic_slug}/{section_slug}/{content_type}"
    Examples:
      "rag/chunking/base_content"
      "rag/chunking/quiz"
      "rag/chunking/style_practical"
      "rag/shell"
    """

    def _redis_key(self, cache_key: str) -> str:
        return f"content:{cache_key}"

    async def get(self, db: AsyncSession, cache_key: str) -> str | None:
        """Get cached content, checking Redis then PostgreSQL."""
        # L1: Redis
        redis_key = self._redis_key(cache_key)
        cached = await cache_service.get(redis_key)
        if cached:
            log.debug("Content cache hit (Redis)", key=cache_key)
            return cached

        # L2: PostgreSQL
        result = await db.execute(
            select(GeneratedContent).where(GeneratedContent.cache_key == cache_key)
        )
        row = result.scalar_one_or_none()
        if row:
            log.debug("Content cache hit (PostgreSQL)", key=cache_key)
            # Warm up Redis
            await cache_service.set(redis_key, row.content, ttl=settings.CACHE_TTL_HOT)
            return row.content

        log.debug("Content cache miss", key=cache_key)
        return None

    async def set(
        self,
        db: AsyncSession,
        cache_key: str,
        content: str,
        provider_used: str,
        model_used: str,
        tokens_input: int = 0,
        tokens_output: int = 0,
    ) -> None:
        """Store generated content in both Redis and PostgreSQL."""
        # L1: Redis
        redis_key = self._redis_key(cache_key)
        await cache_service.set(redis_key, content, ttl=settings.CACHE_TTL_HOT)

        # L2: PostgreSQL (upsert)
        result = await db.execute(
            select(GeneratedContent).where(GeneratedContent.cache_key == cache_key)
        )
        existing = result.scalar_one_or_none()

        if existing is None:
            db.add(
                GeneratedContent(
                    cache_key=cache_key,
                    content=content,
                    provider_used=provider_used,
                    model_used=model_used,
                    tokens_input=tokens_input,
                    tokens_output=tokens_output,
                )
            )
            await db.flush()
            log.info(
                "Content cached",
                key=cache_key,
                provider=provider_used,
                tokens=tokens_input + tokens_output,
            )

    async def exists(self, db: AsyncSession, cache_key: str) -> bool:
        return await self.get(db, cache_key) is not None


content_cache = ContentCacheService()
