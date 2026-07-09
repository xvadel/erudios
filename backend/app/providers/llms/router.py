from __future__ import annotations

import time
import structlog

from app.providers.llms.base import LLMProvider, LLMResponse
from app.providers.llms.budget import BudgetTracker, Provider, TaskType, budget_tracker
from app.providers.llms.gemini import GeminiProvider
from app.providers.llms.groq import GroqProvider
from app.providers.llms.huggingface import HuggingFaceProvider
from app.config import settings
from app.core.exceptions import ProviderExhaustedError, ConfigurationError
from app.core.metrics import LLM_REQUESTS, LLM_TOKENS, LLM_LATENCY

log = structlog.get_logger()


# Task → preferred provider order (cheapest/fastest first, most capable last)
TASK_ROUTING: dict[TaskType, list[Provider]] = {
    TaskType.CLASSIFY: [
        Provider.GROQ_GEMMA,
        Provider.GROQ_LLAMA,
        Provider.GEMINI_FLASH,
    ],
    TaskType.SHORT_GEN: [
        Provider.GROQ_LLAMA,
        Provider.GEMINI_FLASH,
        Provider.GROQ_GEMMA,
    ],
    TaskType.MEDIUM_GEN: [
        Provider.GEMINI_FLASH,
        Provider.GROQ_LLAMA,
    ],
    TaskType.DEEP_GEN: [
        Provider.GEMINI_FLASH,
        Provider.GEMINI_25_FLASH,
        Provider.GROQ_LLAMA,
    ],
    TaskType.REASONING: [
        Provider.GEMINI_25_FLASH,
        Provider.GEMINI_FLASH,
        Provider.GROQ_LLAMA,
    ],
    TaskType.EMBEDDING: [
        Provider.HUGGINGFACE,
    ],
}

# Estimated tokens per task type (for budget pre-check)
TASK_TOKEN_ESTIMATES: dict[TaskType, int] = {
    TaskType.CLASSIFY: 150,
    TaskType.SHORT_GEN: 400,
    TaskType.MEDIUM_GEN: 700,
    TaskType.DEEP_GEN: 1200,
    TaskType.REASONING: 1500,
    TaskType.EMBEDDING: 1,  # Embeddings use request count, not tokens
}


def _build_provider(provider: Provider) -> LLMProvider | None:
    """Instantiate a provider if its API key is configured."""
    match provider:
        case Provider.GEMINI_FLASH:
            if settings.has_gemini:
                return GeminiProvider(model=Provider.GEMINI_FLASH)
        case Provider.GEMINI_25_FLASH:
            if settings.has_gemini:
                return GeminiProvider(model=Provider.GEMINI_25_FLASH)
        case Provider.GROQ_LLAMA:
            if settings.has_groq:
                return GroqProvider(model=Provider.GROQ_LLAMA)
        case Provider.GROQ_GEMMA:
            if settings.has_groq:
                return GroqProvider(model=Provider.GROQ_GEMMA)
        case Provider.HUGGINGFACE:
            return HuggingFaceProvider()
    return None


class ProviderRouter:
    """
    Routes LLM requests to the best available free-tier provider.
    Respects daily token budgets, provider availability, and task complexity.
    """

    def __init__(self, tracker: BudgetTracker = budget_tracker):
        self._tracker = tracker

    async def route(
        self,
        task: TaskType,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 1024,
        json_mode: bool = False,
    ) -> LLMResponse:
        """Try providers in priority order, skip exhausted or unconfigured ones."""
        estimated_tokens = TASK_TOKEN_ESTIMATES.get(task, 500)
        preferred_order = TASK_ROUTING.get(task, list(TASK_ROUTING[TaskType.MEDIUM_GEN]))

        for provider_id in preferred_order:
            provider = _build_provider(provider_id)
            if provider is None:
                continue  # Not configured

            if not await self._tracker.can_use(provider_id, estimated_tokens):
                log.warning("Provider budget exhausted, trying next", provider=provider_id)
                continue

            try:
                log.info(
                    "Routing LLM request",
                    task=task,
                    provider=provider_id,
                    estimated_tokens=estimated_tokens,
                )
                start_time = time.perf_counter()
                response = await provider.generate(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    json_mode=json_mode,
                )
                duration = time.perf_counter() - start_time
                
                LLM_LATENCY.labels(provider=provider_id, task_type=task).observe(duration)
                LLM_REQUESTS.labels(provider=provider_id, task_type=task, status="success").inc()
                LLM_TOKENS.labels(provider=provider_id, token_type="input").inc(response.tokens_input)
                LLM_TOKENS.labels(provider=provider_id, token_type="output").inc(response.tokens_output)
                LLM_TOKENS.labels(provider=provider_id, token_type="total").inc(response.total_tokens)

                # Record actual usage
                await self._tracker.record_usage(provider_id, response.total_tokens)
                return response

            except Exception as exc:
                LLM_REQUESTS.labels(provider=provider_id, task_type=task, status="error").inc()
                log.error(
                    "Provider failed, trying next",
                    provider=provider_id,
                    error=str(exc),
                )
                continue

        raise ProviderExhaustedError(
            "All LLM providers are exhausted or unavailable. "
            "Content generation has been queued and will complete when quotas reset."
        )

    async def get_status(self) -> dict:
        """Return provider status for the health endpoint."""
        return await self._tracker.get_all_status()


# Singleton router
provider_router = ProviderRouter()
