from __future__ import annotations

import json
from typing import Any

import structlog
import redis.asyncio as aioredis

from app.config import settings
from app.core.metrics import CACHE_OPERATIONS

log = structlog.get_logger()


class CacheService:
    """Redis-backed cache with JSON serialization."""

    def __init__(self):
        self._redis: aioredis.Redis | None = None

    async def connect(self) -> None:
        self._redis = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )
        await self._redis.ping()

    async def disconnect(self) -> None:
        if self._redis:
            await self._redis.aclose()

    def _client(self) -> aioredis.Redis:
        if self._redis is None:
            raise RuntimeError("Cache not connected. Call connect() first.")
        return self._redis

    async def get(self, key: str) -> Any | None:
        try:
            raw = await self._client().get(key)
            if raw is None:
                CACHE_OPERATIONS.labels(operation="get", result="miss").inc()
                return None
            CACHE_OPERATIONS.labels(operation="get", result="hit").inc()
            try:
                return json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                return raw
        except Exception:
            CACHE_OPERATIONS.labels(operation="get", result="error").inc()
            raise

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        try:
            serialized = json.dumps(value) if not isinstance(value, str) else value
            if ttl:
                await self._client().setex(key, ttl, serialized)
            else:
                await self._client().set(key, serialized)
            CACHE_OPERATIONS.labels(operation="set", result="success").inc()
        except Exception:
            CACHE_OPERATIONS.labels(operation="set", result="error").inc()
            raise

    async def delete(self, key: str) -> None:
        try:
            await self._client().delete(key)
            CACHE_OPERATIONS.labels(operation="delete", result="success").inc()
        except Exception:
            CACHE_OPERATIONS.labels(operation="delete", result="error").inc()
            raise

    async def exists(self, key: str) -> bool:
        return bool(await self._client().exists(key))

    async def increment(self, key: str, amount: int = 1, ttl: int | None = None) -> int:
        client = self._client()
        new_val = await client.incrby(key, amount)
        if ttl and new_val == amount:
            # First increment — set TTL
            await client.expire(key, ttl)
        return new_val

    async def get_many(self, keys: list[str]) -> dict[str, Any]:
        if not keys:
            return {}
        values = await self._client().mget(keys)
        result = {}
        for key, raw in zip(keys, values):
            if raw is not None:
                try:
                    result[key] = json.loads(raw)
                except (json.JSONDecodeError, TypeError):
                    result[key] = raw
        return result


cache_service = CacheService()
