"""
Embeddings provider package.

Provides EmbeddingProvider abstraction + Qdrant vector store.
Use get_embedding_provider() for the configured singleton.
"""
from app.providers.embeddings.base import EmbeddingProvider
from app.providers.embeddings.huggingface import LocalEmbeddingProvider, HuggingFaceAPIEmbeddingProvider
from app.providers.embeddings.qdrant_store import QdrantStore, SearchResult, qdrant_store

__all__ = [
    "EmbeddingProvider",
    "LocalEmbeddingProvider",
    "HuggingFaceAPIEmbeddingProvider",
    "QdrantStore",
    "SearchResult",
    "qdrant_store",
    "get_embedding_provider",
]


def get_embedding_provider() -> EmbeddingProvider:
    """
    Return the best available embedding provider.
    Prefers HuggingFace API if key is set, falls back to local sentence-transformers.
    """
    from app.config import settings
    if settings.has_huggingface:
        try:
            return HuggingFaceAPIEmbeddingProvider()
        except RuntimeError:
            pass
    return LocalEmbeddingProvider()
