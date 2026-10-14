from __future__ import annotations

import structlog
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.providers.llms.base import LLMProvider, LLMResponse
from app.config import settings

log = structlog.get_logger()


class GroqProvider(LLMProvider):
    def __init__(self, model: str = "llama-3.3-70b-versatile"):
        self._model = model
        self._client = None

    def _get_client(self):
        if self._client is None:
            from groq import AsyncGroq
            self._client = AsyncGroq(api_key=settings.GROQ_API_KEY)
        return self._client

    @property
    def provider_name(self) -> str:
        return "groq"

    @property
    def model_name(self) -> str:
        return self._model

    @retry(
        retry=retry_if_exception_type(Exception),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 1024,
        json_mode: bool = False,
    ) -> LLMResponse:
        client = self._get_client()

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        kwargs: dict = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        response = await client.chat.completions.create(**kwargs)

        usage = response.usage
        tokens_input = usage.prompt_tokens if usage else 0
        tokens_output = usage.completion_tokens if usage else 0

        log.debug(
            "Groq generation complete",
            model=self._model,
            tokens_in=tokens_input,
            tokens_out=tokens_output,
        )

        return LLMResponse(
            content=response.choices[0].message.content or "",
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            provider=self.provider_name,
            model=self._model,
        )

    async def is_available(self) -> bool:
        return bool(settings.GROQ_API_KEY)
