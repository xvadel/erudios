from __future__ import annotations

import hashlib
import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.resource import Resource
from app.models.topic import Topic
from app.providers.embeddings import get_embedding_provider, qdrant_store

log = structlog.get_logger()


class RAGIndexer:
    """
    Indexes topic resources into Qdrant for retrieval-augmented generation.

    Each resource is embedded as: "<title>. <snippet_if_any>"
    The payload stored alongside each vector includes:
      - topic_slug, title, url, source_type, author, composite_score
    """

    async def index_topic(self, db: AsyncSession, topic_slug: str) -> int:
        """
        Embed all resources for a topic and upsert into Qdrant.
        Returns the number of vectors indexed.
        """
        topic_result = await db.execute(
            select(Topic).where(Topic.slug == topic_slug)
        )
        topic = topic_result.scalar_one_or_none()
        if not topic:
            log.warning("RAGIndexer: topic not found", slug=topic_slug)
            return 0

        resources_result = await db.execute(
            select(Resource).where(
                Resource.topic_id == topic.id,
                Resource.is_alive == True,
            ).order_by(Resource.composite_score.desc()).limit(50)
        )
        resources = list(resources_result.scalars().all())

        if not resources:
            log.info("RAGIndexer: no resources to index", topic=topic_slug)
            return 0

        provider = get_embedding_provider()
        await qdrant_store.ensure_collection(dimensions=provider.dimensions)

        # Build texts for embedding
        texts = [
            f"{r.title}. {r.resource_metadata.get('snippet', '')}"[:512]
            for r in resources
        ]

        vectors = await provider.embed(texts)

        ids = [_resource_vector_id(topic_slug, str(r.id)) for r in resources]
        payloads = [
            {
                "topic_slug": topic_slug,
                "resource_id": str(r.id),
                "title": r.title,
                "url": r.url,
                "source_type": r.source_type,
                "author": r.author or "",
                "composite_score": r.composite_score,
                "text": texts[i],
            }
            for i, r in enumerate(resources)
        ]

        await qdrant_store.upsert(ids=ids, vectors=vectors, payloads=payloads)
        log.info("RAGIndexer: indexed resources", topic=topic_slug, count=len(resources))
        return len(resources)

    async def index_all_topics(self, db: AsyncSession) -> dict[str, int]:
        """Index resources for every topic that has resources."""
        topics_result = await db.execute(select(Topic))
        topics = list(topics_result.scalars().all())
        counts: dict[str, int] = {}
        for topic in topics:
            try:
                n = await self.index_topic(db, topic.slug)
                if n > 0:
                    counts[topic.slug] = n
            except Exception as exc:
                log.error("RAGIndexer: failed to index topic", topic=topic.slug, error=str(exc))
        return counts


def _resource_vector_id(topic_slug: str, resource_id: str) -> str:
    """Deterministic UUID-compatible string ID for a resource vector."""
    # Qdrant accepts string IDs
    return hashlib.sha1(f"{topic_slug}:{resource_id}".encode()).hexdigest()[:32]


rag_indexer = RAGIndexer()
