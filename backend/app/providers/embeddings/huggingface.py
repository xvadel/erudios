from __future__ import annotations

import asyncio
import structlog
from functools import lru_cache

from app.providers.embeddings.base import EmbeddingProvider

log = structlog.get_logger()

# Model used: all-MiniLM-L6-v2 is small (22M params), fast, and produces 384-dim vectors.
# It runs entirely locally — no API key needed.
_MODEL_NAME = "all-MiniLM-L6-v2"
_DIMENSIONS = 384


@lru_cache(maxsize=1)
def _get_model():
    """Lazily load the sentence-transformers model (cached singleton)."""
    from sentence_transformers import SentenceTransformer
    log.info("Loading sentence-transformers model", model=_MODEL_NAME)
    return SentenceTransformer(_MODEL_NAME)


class LocalEmbeddingProvider(EmbeddingProvider):
    """
    Local embedding provider using sentence-transformers.
    Runs entirely on CPU — no API key or internet required.
    Model: all-MiniLM-L6-v2 (384 dimensions, fast and accurate).
    """

    @property
    def provider_name(self) -> str:
        return "local-sentence-transformers"

    @property
    def dimensions(self) -> int:
        return _DIMENSIONS

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed texts in a thread pool to avoid blocking the event loop."""
        if not texts:
            return []
        loop = asyncio.get_event_loop()
        vectors = await loop.run_in_executor(
            None,  # Default thread pool
            lambda: _get_model().encode(texts, convert_to_numpy=True).tolist(),
        )
        return vectors


class HuggingFaceAPIEmbeddingProvider(EmbeddingProvider):
    """
    Embedding via HuggingFace Inference API.
    Requires HUGGINGFACE_API_KEY. Uses feature-extraction endpoint.
    Falls back to LocalEmbeddingProvider if API fails.
    """

    _HF_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

    def __init__(self) -> None:
        from app.config import settings
        if not settings.HUGGINGFACE_API_KEY:
            raise RuntimeError("HUGGINGFACE_API_KEY not configured")
        self._api_key = settings.HUGGINGFACE_API_KEY

    @property
    def provider_name(self) -> str:
        return "huggingface-api"

    @property
    def dimensions(self) -> int:
        return _DIMENSIONS

    async def embed(self, texts: list[str]) -> list[list[float]]:
        import httpx
        url = f"https://api-inference.huggingface.co/pipeline/feature-extraction/{self._HF_MODEL}"
        headers = {"Authorization": f"Bearer {self._api_key}"}
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, headers=headers, json={"inputs": texts})
            resp.raise_for_status()
            data = resp.json()
        # HF returns list[list[float]] or list[list[list[float]]] (mean-pool if nested)
        result = []
        for vec in data:
            if isinstance(vec[0], list):
                # Mean-pool over token dimension
                pooled = [sum(dim) / len(dim) for dim in zip(*vec)]
                result.append(pooled)
            else:
                result.append(vec)
        return result
