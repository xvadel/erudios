from __future__ import annotations

import uuid
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.api.v1.auth import get_current_user
from app.models.user import User
from app.modules.topic_graph.service import topic_graph_service
from app.modules.mastery.analytics import (
    quiz_analytics_service,
    ConceptPerformance,
    RepeatedMistake,
    DailyScoreTrend,
    LearningSummary,
)

router = APIRouter()


@router.get("/concepts/weak", response_model=list[ConceptPerformance])
async def get_weak_concepts(
    topic_slug: str,
    threshold: float = Query(default=60.0, ge=0.0, le=100.0),
    request: Request = None,
    db: AsyncSession = Depends(get_db),
):
    """Get list of sub-concepts where the user accuracy is below a threshold."""
    user: User = await get_current_user(request, db)
    topic = await topic_graph_service.get_by_slug(db, topic_slug)
    return await quiz_analytics_service.get_weak_concepts(
        db=db, user_id=user.id, topic_id=topic.id, threshold=threshold
    )


@router.get("/concepts/strong", response_model=list[ConceptPerformance])
async def get_strong_concepts(
    topic_slug: str,
    threshold: float = Query(default=85.0, ge=0.0, le=100.0),
    request: Request = None,
    db: AsyncSession = Depends(get_db),
):
    """Get list of sub-concepts where the user accuracy is at or above a threshold."""
    user: User = await get_current_user(request, db)
    topic = await topic_graph_service.get_by_slug(db, topic_slug)
    return await quiz_analytics_service.get_strong_concepts(
        db=db, user_id=user.id, topic_id=topic.id, threshold=threshold
    )


@router.get("/mistakes/repeated", response_model=list[RepeatedMistake])
async def get_repeated_mistakes(
    limit: int = Query(default=10, ge=1, le=50),
    request: Request = None,
    db: AsyncSession = Depends(get_db),
):
    """Fetch top concepts where user makes repeated mistakes."""
    user: User = await get_current_user(request, db)
    return await quiz_analytics_service.get_repeated_mistakes(
        db=db, user_id=user.id, limit=limit
    )


@router.get("/trends", response_model=list[DailyScoreTrend])
async def get_topic_trends(
    topic_slug: str,
    days: int = Query(default=30, ge=1, le=365),
    request: Request = None,
    db: AsyncSession = Depends(get_db),
):
    """Returns daily average score trend for a given topic."""
    user: User = await get_current_user(request, db)
    topic = await topic_graph_service.get_by_slug(db, topic_slug)
    return await quiz_analytics_service.get_topic_performance_trend(
        db=db, user_id=user.id, topic_id=topic.id, days=days
    )


@router.get("/summary", response_model=LearningSummary)
async def get_learning_summary(
    request: Request = None,
    db: AsyncSession = Depends(get_db),
):
    """Fetch user streak, aggregate score velocity, and total mastery metrics."""
    user: User = await get_current_user(request, db)
    return await quiz_analytics_service.get_learning_summary(db=db, user_id=user.id)
