from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
import structlog

from app.config import settings

log = structlog.get_logger()

_COLLECTION = settings.QDRANT_COLLECTION


@dataclass
class SearchResult:
    """A single result returned from Qdrant vector search."""
    id: str
    score: float
    payload: dict = field(default_factory=dict)

    @property
    def text(self) -> str:
        return self.payload.get("text", "")

    @property
    def url(self) -> str:
        return self.payload.get("url", "")

    @property
    def title(self) -> str:
        return self.payload.get("title", "")

    @property
    def topic_slug(self) -> str:
        return self.payload.get("topic_slug", "")


class QdrantStore:
    """
    Async wrapper around the Qdrant vector database.
    Handles collection creation, upsert, and semantic search.
    """

    def __init__(self, collection: str = _COLLECTION) -> None:
        self._collection = collection
        self._client: Any | None = None

    def _get_client(self):
        from qdrant_client import AsyncQdrantClient
        if self._client is None:
            self._client = AsyncQdrantClient(url=settings.QDRANT_URL)
        return self._client

    async def ensure_collection(self, dimensions: int) -> None:
        """Create the collection if it does not exist."""
        from qdrant_client.models import Distance, VectorParams
        client = self._get_client()
        existing = await client.collection_exists(self._collection)
        if not existing:
            await client.create_collection(
                collection_name=self._collection,
                vectors_config=VectorParams(size=dimensions, distance=Distance.COSINE),
            )
            log.info("Qdrant collection created", collection=self._collection, dim=dimensions)

    async def upsert(
        self,
        ids: list[str],
        vectors: list[list[float]],
        payloads: list[dict],
    ) -> None:
        """Upsert vectors with payloads into the collection."""
        from qdrant_client.models import PointStruct
        client = self._get_client()
        points = [
            PointStruct(id=id_, vector=vec, payload=payload)
            for id_, vec, payload in zip(ids, vectors, payloads)
        ]
        await client.upsert(collection_name=self._collection, points=points, wait=True)
        log.info("Qdrant upsert complete", collection=self._collection, count=len(points))

    async def search(
        self,
        query_vector: list[float],
        limit: int = 5,
        topic_slug: str | None = None,
    ) -> list[SearchResult]:
        """Semantic search with optional topic filter."""
        from qdrant_client.models import Filter, FieldCondition, MatchValue
        client = self._get_client()

        query_filter = None
        if topic_slug:
            query_filter = Filter(
                must=[FieldCondition(key="topic_slug", match=MatchValue(value=topic_slug))]
            )

        results = await client.search(
            collection_name=self._collection,
            query_vector=query_vector,
            limit=limit,
            query_filter=query_filter,
            with_payload=True,
        )
        return [
            SearchResult(id=str(r.id), score=r.score, payload=r.payload or {})
            for r in results
        ]

    async def delete_by_topic(self, topic_slug: str) -> None:
        """Remove all vectors for a given topic (useful for re-indexing)."""
        from qdrant_client.models import Filter, FieldCondition, MatchValue
        client = self._get_client()
        await client.delete(
            collection_name=self._collection,
            points_selector=Filter(
                must=[FieldCondition(key="topic_slug", match=MatchValue(value=topic_slug))]
            ),
        )
        log.info("Qdrant deleted topic vectors", topic=topic_slug)


# Singleton
qdrant_store = QdrantStore()
