from __future__ import annotations

from abc import ABC, abstractmethod


class EmbeddingProvider(ABC):
    """Abstract base for text embedding providers."""

    @property
    @abstractmethod
    def provider_name(self) -> str: ...

    @property
    @abstractmethod
    def dimensions(self) -> int:
        """Dimensionality of the output embedding vectors."""
        ...

    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]:
        """
        Embed a batch of texts. Returns one vector per input text.
        Raises RuntimeError if the provider is unavailable.
        """
        ...

    async def embed_one(self, text: str) -> list[float]:
        """Convenience wrapper for a single text."""
        results = await self.embed([text])
        return results[0]
