from __future__ import annotations

import structlog
import httpx

from app.providers.llms.base import LLMProvider, LLMResponse
from app.config import settings

log = structlog.get_logger()

HF_API_URL = "https://api-inference.huggingface.co/models"

# Curated free HF models good for text generation
HF_GENERATION_MODELS = {
    "default": "mistralai/Mistral-7B-Instruct-v0.3",
    "fast": "microsoft/phi-2",
}


class HuggingFaceProvider(LLMProvider):
    def __init__(self, model: str = HF_GENERATION_MODELS["default"]):
        self._model = model

    @property
    def provider_name(self) -> str:
        return "huggingface"

    @property
    def model_name(self) -> str:
        return self._model

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 512,
        json_mode: bool = False,
    ) -> LLMResponse:
        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt

        headers = {}
        if settings.HUGGINGFACE_API_KEY:
            headers["Authorization"] = f"Bearer {settings.HUGGINGFACE_API_KEY}"

        payload = {
            "inputs": full_prompt,
            "parameters": {
                "max_new_tokens": max_tokens,
                "temperature": temperature,
                "return_full_text": False,
            },
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{HF_API_URL}/{self._model}",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            result = response.json()

        content = ""
        if isinstance(result, list) and result:
            content = result[0].get("generated_text", "")
        elif isinstance(result, dict):
            content = result.get("generated_text", "")

        # HF doesn't return token counts — estimate
        estimated_input = len(full_prompt.split()) * 1.3
        estimated_output = len(content.split()) * 1.3

        return LLMResponse(
            content=content,
            tokens_input=int(estimated_input),
            tokens_output=int(estimated_output),
            provider=self.provider_name,
            model=self._model,
        )

    async def is_available(self) -> bool:
        # HuggingFace works without a key (rate limited) or with a free key
        return True
