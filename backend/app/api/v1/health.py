from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app.providers.llms.budget import budget_tracker
from app.config import settings

router = APIRouter()


class ProviderStatus(BaseModel):
    status: str
    daily_budget_remaining_pct: float | None = None
    note: str | None = None


class FeatureStatus(BaseModel):
    resource_discovery: str
    curriculum_generation: str
    artifact_generation: str
    rag_tutor: str


class HealthResponse(BaseModel):
    status: str
    version: str
    providers: dict[str, ProviderStatus]
    features: FeatureStatus


@router.get("", response_model=HealthResponse)
async def health_check():
    """
    System health and provider status.
    Shows which API keys are configured and what features are available.
    """
    budget_status = await budget_tracker.get_all_status()

    providers: dict[str, ProviderStatus] = {}

    # Gemini
    if settings.has_gemini:
        g = budget_status.get("gemini-2.0-flash", {})
        remaining_pct = 100.0 - g.get("percent_used", 0)
        providers["gemini"] = ProviderStatus(
            status="active",
            daily_budget_remaining_pct=round(remaining_pct, 1),
        )
    else:
        providers["gemini"] = ProviderStatus(
            status="not_configured",
            note="Set GEMINI_API_KEY in .env to enable",
        )

    # Groq
    if settings.has_groq:
        g = budget_status.get("llama-3.3-70b-versatile", {})
        remaining_pct = 100.0 - g.get("percent_used", 0)
        providers["groq"] = ProviderStatus(
            status="active",
            daily_budget_remaining_pct=round(remaining_pct, 1),
        )
    else:
        providers["groq"] = ProviderStatus(
            status="not_configured",
            note="Set GROQ_API_KEY in .env to enable",
        )

    # HuggingFace
    if settings.has_huggingface:
        providers["huggingface"] = ProviderStatus(status="active")
    else:
        providers["huggingface"] = ProviderStatus(
            status="optional",
            note="Set HUGGINGFACE_API_KEY for better embeddings",
        )

    # Tavily
    if settings.has_tavily:
        providers["tavily_search"] = ProviderStatus(status="active")
    else:
        providers["tavily_search"] = ProviderStatus(
            status="optional",
            note="Using DuckDuckGo fallback. Set TAVILY_API_KEY for better search quality.",
        )

    has_llm = bool(settings.available_llm_providers)

    features = FeatureStatus(
        resource_discovery="full" if has_llm else "limited (no LLM ranking)",
        curriculum_generation="full" if has_llm else "unavailable",
        artifact_generation="full" if has_llm else "unavailable",
        rag_tutor="available" if has_llm else "unavailable",
    )

    return HealthResponse(
        status="healthy" if has_llm else "degraded",
        version=settings.APP_VERSION,
        providers=providers,
        features=features,
    )
