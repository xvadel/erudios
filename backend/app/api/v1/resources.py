from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.models.resource import Resource
from app.models.topic import Topic
from app.modules.research.sources.web import DuckDuckGoSource, TavilySource
from app.modules.research.sources.github import GitHubSource
from app.modules.research.sources.academic import OpenAlexSource
from app.modules.research.ranker import build_ranker
from app.core.exceptions import NotFoundError
from app.config import settings
from app.api.v1.auth import get_current_user
from app.modules.research.feedback import resource_feedback_service

router = APIRouter()


class FeedbackOut(BaseModel):
    resource_id: uuid.UUID
    rating: int
    bookmarked: bool
    completed: bool
    time_spent_seconds: int

    model_config = {"from_attributes": True}


class ResourceOut(BaseModel):
    id: uuid.UUID
    title: str
    url: str
    source_type: str
    author: str | None
    published_at: date | None
    trust_score: float
    quality_score: float
    composite_score: float
    user_feedback: FeedbackOut | None = None

    model_config = {"from_attributes": True}


@router.get("/topics/{topic_slug}", response_model=list[ResourceOut])
async def get_resources_for_topic(
    topic_slug: str,
    request: Request,
    source_type: str | None = Query(None, description="Filter by: blog|github|paper|video"),
    min_score: float = Query(0.0, ge=0, le=100),
    limit: int = Query(20, le=50),
    db: AsyncSession = Depends(get_db),
):
    """Get ranked resources for a topic. Returns cached results instantly."""
    # Resolve optional user
    user = None
    try:
        user = await get_current_user(request, db)
    except Exception:
        pass

    # Resolve topic
    result = await db.execute(select(Topic).where(Topic.slug == topic_slug))
    topic = result.scalar_one_or_none()
    if not topic:
        raise NotFoundError(f"Topic '{topic_slug}' not found")

    query = select(Resource).where(
        Resource.topic_id == topic.id,
        Resource.is_alive == True,
        Resource.composite_score >= min_score,
    )
    if source_type:
        query = query.where(Resource.source_type == source_type)

    query = query.order_by(Resource.composite_score.desc()).limit(limit)
    result = await db.execute(query)
    resources = result.scalars().all()

    # Load feedback map if authenticated
    feedback_map = {}
    if user and resources:
        res_ids = [r.id for r in resources]
        from app.models.resource_feedback import ResourceFeedback
        fb_res = await db.execute(
            select(ResourceFeedback).where(
                ResourceFeedback.user_id == user.id,
                ResourceFeedback.resource_id.in_(res_ids),
            )
        )
        for fb in fb_res.scalars().all():
            feedback_map[fb.resource_id] = fb

    out = []
    for r in resources:
        item = ResourceOut.model_validate(r)
        if r.id in feedback_map:
            item.user_feedback = FeedbackOut.model_validate(feedback_map[r.id])
        out.append(item)

    return out


@router.post("/topics/{topic_slug}/discover")
async def discover_resources(
    topic_slug: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Trigger resource discovery for a topic.
    Runs in background — returns immediately.
    """
    result = await db.execute(select(Topic).where(Topic.slug == topic_slug))
    topic = result.scalar_one_or_none()
    if not topic:
        raise NotFoundError(f"Topic '{topic_slug}' not found")

    background_tasks.add_task(_run_discovery, topic_slug, topic.id)

    return {
        "message": f"Resource discovery started for '{topic_slug}'",
        "status": "running",
    }


async def _run_discovery(topic_slug: str, topic_id: uuid.UUID) -> None:
    """Background task: discover and rank resources for a topic."""
    from app.db.session import AsyncSessionLocal
    import structlog
    log = structlog.get_logger()

    async with AsyncSessionLocal() as db:
        try:
            sources = []
            # Always use DuckDuckGo (free)
            sources.append(DuckDuckGoSource())
            # Use Tavily if available (better quality)
            if settings.has_tavily:
                sources.append(TavilySource())
            # GitHub repos
            sources.append(GitHubSource())
            # Academic papers (OpenAlex — free)
            sources.append(OpenAlexSource())

            ranker = await build_ranker(db)
            all_raw = []

            for source in sources:
                raw = await source.discover(topic_slug, limit=settings.SEARCH_RESULTS_PER_SOURCE)
                all_raw.extend(raw)
                log.info("Source discovered", source=source.source_type, count=len(raw))

            ranked = ranker.rank(all_raw)

            # Upsert into database
            saved = 0
            for raw, trust, quality, composite in ranked[:settings.MAX_RESOURCES_PER_TOPIC]:
                # Check for duplicate URL
                existing = await db.execute(
                    select(Resource).where(Resource.url == raw.url)
                )
                if existing.scalar_one_or_none():
                    continue

                db.add(Resource(
                    topic_id=topic_id,
                    title=raw.title,
                    url=raw.url,
                    source_type=raw.source_type,
                    author=raw.author,
                    published_at=raw.published_at,
                    trust_score=trust,
                    quality_score=quality,
                    composite_score=composite,
                    resource_metadata=raw.signals,
                ))
                saved += 1

            await db.commit()
            log.info("Resource discovery complete", topic=topic_slug, saved=saved)

        except Exception as exc:
            log.error("Resource discovery failed", topic=topic_slug, error=str(exc))
            await db.rollback()


# ── Resource Feedback Schema ──────────────────────────────────────────────────

class FeedbackRequest(BaseModel):
    rating: int | None = None  # 1 = helpful, -1 = not helpful, 0 = neutral
    bookmarked: bool | None = None
    completed: bool | None = None
    time_spent_seconds: int = 0


# ── Feedback Routes ───────────────────────────────────────────────────────────

@router.get("/bookmarks", response_model=list[ResourceOut])
async def get_user_bookmarks(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve all resources currently bookmarked by the user."""
    user = await get_current_user(request, db)
    resources = await resource_feedback_service.get_user_bookmarks(db, user.id)
    
    # Load feedback map to enrich bookmarks
    feedback_map = {}
    if resources:
        res_ids = [r.id for r in resources]
        from app.models.resource_feedback import ResourceFeedback
        fb_res = await db.execute(
            select(ResourceFeedback).where(
                ResourceFeedback.user_id == user.id,
                ResourceFeedback.resource_id.in_(res_ids),
            )
        )
        for fb in fb_res.scalars().all():
            feedback_map[fb.resource_id] = fb

    out = []
    for r in resources:
        item = ResourceOut.model_validate(r)
        if r.id in feedback_map:
            item.user_feedback = FeedbackOut.model_validate(feedback_map[r.id])
        out.append(item)
    return out


@router.post("/{resource_id}/feedback", response_model=FeedbackOut)
async def submit_resource_feedback(
    resource_id: uuid.UUID,
    body: FeedbackRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Record or edit user feedback (bookmarking, ratings, completion) for a resource.
    Recalculates composite score and handles spam protection.
    """
    user = await get_current_user(request, db)
    fb = await resource_feedback_service.upsert_feedback(
        db=db,
        user_id=user.id,
        resource_id=resource_id,
        rating=body.rating,
        bookmarked=body.bookmarked,
        completed=body.completed,
        time_spent_seconds=body.time_spent_seconds,
    )
    return fb


@router.get("/{resource_id}/feedback", response_model=FeedbackOut | None)
async def get_resource_feedback(
    resource_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Get the authenticated user's feedback details for a specific resource."""
    user = await get_current_user(request, db)
    fb = await resource_feedback_service.get_user_feedback(db, user.id, resource_id)
    return fb
