from __future__ import annotations

import structlog
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.providers.llms.base import LLMProvider, LLMResponse
from app.config import settings

log = structlog.get_logger()


class GeminiProvider(LLMProvider):
    def __init__(self, model: str = "gemini-2.0-flash"):
        self._model = model
        self._client = None

    def _get_client(self):
        if self._client is None:
            import google.generativeai as genai
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self._client = genai.GenerativeModel(
                model_name=self._model,
                generation_config={"response_mime_type": "application/json"}
                if False  # Set dynamically in generate()
                else {},
            )
        return self._client

    @property
    def provider_name(self) -> str:
        return "gemini"

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
        import google.generativeai as genai

        genai.configure(api_key=settings.GEMINI_API_KEY)

        config_kwargs: dict = {
            "temperature": temperature,
            "max_output_tokens": max_tokens,
        }
        if json_mode:
            config_kwargs["response_mime_type"] = "application/json"

        generation_config = genai.GenerationConfig(**config_kwargs)

        model = genai.GenerativeModel(
            model_name=self._model,
            generation_config=generation_config,
            system_instruction=system_prompt,
        )

        response = await model.generate_content_async(prompt)

        tokens_input = response.usage_metadata.prompt_token_count or 0
        tokens_output = response.usage_metadata.candidates_token_count or 0

        log.debug(
            "Gemini generation complete",
            model=self._model,
            tokens_in=tokens_input,
            tokens_out=tokens_output,
        )

        return LLMResponse(
            content=response.text,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            provider=self.provider_name,
            model=self._model,
        )

    async def is_available(self) -> bool:
        return bool(settings.GEMINI_API_KEY)
