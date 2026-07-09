from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel
from prometheus_client import REGISTRY

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


class DiagnosticsStatus(BaseModel):
    cache_hit_ratio_pct: float | None = None
    cache_gets_total: int = 0
    llm_requests_total: int = 0


class HealthResponse(BaseModel):
    status: str
    version: str
    providers: dict[str, ProviderStatus]
    features: FeatureStatus
    diagnostics: DiagnosticsStatus


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

    # Query metrics registry for diagnostics status
    cache_hits = 0
    cache_misses = 0
    llm_requests = 0

    for metric in REGISTRY.collect():
        if metric.name == "erudios_cache_operations_total":
            for sample in metric.samples:
                if sample.labels.get("operation") == "get":
                    if sample.labels.get("result") == "hit":
                        cache_hits += int(sample.value)
                    elif sample.labels.get("result") == "miss":
                        cache_misses += int(sample.value)
        elif metric.name == "erudios_llm_requests_total":
            for sample in metric.samples:
                llm_requests += int(sample.value)

    total_gets = cache_hits + cache_misses
    hit_ratio = round(cache_hits / total_gets * 100, 1) if total_gets > 0 else None

    diagnostics = DiagnosticsStatus(
        cache_hit_ratio_pct=hit_ratio,
        cache_gets_total=total_gets,
        llm_requests_total=llm_requests,
    )

    return HealthResponse(
        status="healthy" if has_llm else "degraded",
        version=settings.APP_VERSION,
        providers=providers,
        features=features,
        diagnostics=diagnostics,
    )
