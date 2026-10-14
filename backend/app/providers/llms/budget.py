from __future__ import annotations

from datetime import date
from enum import StrEnum

import structlog

from app.services.cache import cache_service
from app.config import settings

log = structlog.get_logger()


class Provider(StrEnum):
    GEMINI_FLASH = "gemini-2.0-flash"
    GEMINI_25_FLASH = "gemini-2.5-flash-preview-05-20"
    GROQ_LLAMA = "llama-3.3-70b-versatile"
    GROQ_GEMMA = "gemma2-9b-it"
    HUGGINGFACE = "huggingface"


class TaskType(StrEnum):
    """Task complexity tiers — determines which provider to use."""
    CLASSIFY = "classify"          # Simple classification/extraction (~100 tokens)
    SHORT_GEN = "short_gen"        # Short generation (~300 tokens)
    MEDIUM_GEN = "medium_gen"      # Medium generation (~500 tokens)
    DEEP_GEN = "deep_gen"          # Deep content generation (~800 tokens)
    REASONING = "reasoning"        # Complex reasoning
    EMBEDDING = "embedding"        # Vector embeddings


# Daily token limits per provider model
DAILY_LIMITS: dict[Provider, int] = {
    Provider.GEMINI_FLASH: settings.GEMINI_FLASH_DAILY_TOKEN_LIMIT,
    Provider.GEMINI_25_FLASH: settings.GEMINI_25_FLASH_DAILY_TOKEN_LIMIT,
    Provider.GROQ_LLAMA: settings.GROQ_LLAMA_DAILY_TOKEN_LIMIT,
    Provider.GROQ_GEMMA: settings.GROQ_GEMMA_DAILY_TOKEN_LIMIT,
    Provider.HUGGINGFACE: settings.HUGGINGFACE_DAILY_REQUEST_LIMIT,
}


def _budget_key(provider: Provider) -> str:
    today = date.today().isoformat()
    return f"budget:{provider}:{today}"


class BudgetTracker:
    """
    Redis-based daily token budget tracker.
    Keys expire at midnight (86400s TTL) — resets automatically each day.
    """

    async def get_used(self, provider: Provider) -> int:
        key = _budget_key(provider)
        val = await cache_service.get(key)
        return int(val) if val else 0

    async def get_remaining(self, provider: Provider) -> int:
        used = await self.get_used(provider)
        return max(0, DAILY_LIMITS[provider] - used)

    async def can_use(self, provider: Provider, estimated_tokens: int = 500) -> bool:
        remaining = await self.get_remaining(provider)
        # Alert at 80% usage
        limit = DAILY_LIMITS[provider]
        used = limit - remaining
        if used > limit * 0.8:
            log.warning(
                "Provider budget > 80% consumed",
                provider=provider,
                used=used,
                limit=limit,
            )
        return remaining >= estimated_tokens

    async def record_usage(self, provider: Provider, tokens_used: int) -> None:
        key = _budget_key(provider)
        await cache_service.increment(key, tokens_used, ttl=settings.CACHE_TTL_PROVIDER_BUDGET)

    async def get_all_status(self) -> dict[str, dict]:
        status = {}
        for provider in Provider:
            if provider == Provider.HUGGINGFACE:
                continue
            used = await self.get_used(provider)
            limit = DAILY_LIMITS[provider]
            status[provider] = {
                "used": used,
                "limit": limit,
                "remaining": max(0, limit - used),
                "percent_used": round(used / limit * 100, 1) if limit > 0 else 0,
            }
        return status


budget_tracker = BudgetTracker()
