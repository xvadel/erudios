from __future__ import annotations

import structlog
from app.db.session import AsyncSessionLocal
from app.modules.rag.indexer import rag_indexer

log = structlog.get_logger()


async def index_topic_resources(ctx, topic_slug: str) -> int:
    """arq task to index topic resources into Qdrant."""
    log.info("Starting topic resources indexing background job", topic=topic_slug)
    async with AsyncSessionLocal() as db:
        try:
            count = await rag_indexer.index_topic(db, topic_slug)
            await db.commit()
            log.info("Background RAG indexing complete via arq", topic=topic_slug, count=count)
            return count
        except Exception as exc:
            await db.rollback()
            log.error("Background RAG indexing failed via arq", topic=topic_slug, error=str(exc))
            raise
