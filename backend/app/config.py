from __future__ import annotations

import os
from functools import lru_cache
from typing import Literal

from pydantic import Field, PostgresDsn, RedisDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ──────────────────────────────────────────────────────────
    APP_NAME: str = "Erudios"
    APP_VERSION: str = "0.1.0"
    APP_ENV: Literal["development", "staging", "production"] = "development"
    DEBUG: bool = True
    SECRET_KEY: str = Field(default="change-me-in-production-please")
    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    # ── Database ─────────────────────────────────────────────────────────────
    DATABASE_URL: str = (
        "postgresql+asyncpg://erudios:erudios@localhost:5432/erudios"
    )

    # ── Redis ────────────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"
    CACHE_TTL_HOT: int = 86_400        # 24 hours (Redis L1)
    CACHE_TTL_PROVIDER_BUDGET: int = 86_400  # Resets daily

    # ── Qdrant ───────────────────────────────────────────────────────────────
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_COLLECTION: str = "erudios_resources"

    # ── LLM Providers ────────────────────────────────────────────────────────
    # At least one of these must be set
    GEMINI_API_KEY: str | None = None
    GROQ_API_KEY: str | None = None
    HUGGINGFACE_API_KEY: str | None = None
    OPENROUTER_API_KEY: str | None = None

    # Daily token budgets (conservative defaults)
    GEMINI_FLASH_DAILY_TOKEN_LIMIT: int = 900_000      # ~90% of 1M limit
    GEMINI_25_FLASH_DAILY_TOKEN_LIMIT: int = 400_000
    GROQ_LLAMA_DAILY_TOKEN_LIMIT: int = 900_000        # ~90% of 1M limit
    GROQ_GEMMA_DAILY_TOKEN_LIMIT: int = 13_000         # ~90% of 14.4K limit
    HUGGINGFACE_DAILY_REQUEST_LIMIT: int = 900          # ~90% of 1K limit

    # ── OAuth ────────────────────────────────────────────────────────────────
    GOOGLE_CLIENT_ID: str | None = None
    GOOGLE_CLIENT_SECRET: str | None = None
    GITHUB_CLIENT_ID: str | None = None
    GITHUB_CLIENT_SECRET: str | None = None
    OAUTH_REDIRECT_BASE_URL: str = "http://localhost:8000"

    # ── JWT ──────────────────────────────────────────────────────────────────
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # ── External APIs ────────────────────────────────────────────────────────
    TAVILY_API_KEY: str | None = None            # Optional — better search quality
    GITHUB_TOKEN: str | None = None              # Optional — higher rate limits
    YOUTUBE_API_KEY: str | None = None           # Optional — video resources

    # ── Resource Discovery ───────────────────────────────────────────────────
    RESOURCE_REFRESH_INTERVAL_HOURS: int = 168   # Weekly
    MIN_RESOURCE_TRUST_SCORE: float = 30.0
    MAX_RESOURCES_PER_TOPIC: int = 50
    SEARCH_RESULTS_PER_SOURCE: int = 10

    # ── Seed Data ────────────────────────────────────────────────────────────
    SEED_DATA_DIR: str = "seed"
    AUTO_SEED_ON_STARTUP: bool = True

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_origins(cls, v: str | list) -> list[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    @property
    def has_gemini(self) -> bool:
        return bool(self.GEMINI_API_KEY)

    @property
    def has_groq(self) -> bool:
        return bool(self.GROQ_API_KEY)

    @property
    def has_huggingface(self) -> bool:
        return bool(self.HUGGINGFACE_API_KEY)

    @property
    def has_tavily(self) -> bool:
        return bool(self.TAVILY_API_KEY)

    @property
    def has_github_token(self) -> bool:
        return bool(self.GITHUB_TOKEN)

    @property
    def has_google_oauth(self) -> bool:
        return bool(self.GOOGLE_CLIENT_ID and self.GOOGLE_CLIENT_SECRET)

    @property
    def has_github_oauth(self) -> bool:
        return bool(self.GITHUB_CLIENT_ID and self.GITHUB_CLIENT_SECRET)

    @property
    def available_llm_providers(self) -> list[str]:
        providers = []
        if self.has_gemini:
            providers.append("gemini")
        if self.has_groq:
            providers.append("groq")
        if self.has_huggingface:
            providers.append("huggingface")
        return providers


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
