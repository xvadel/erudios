from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.db.session import get_db
from app.api.v1.auth import get_current_user
from app.models.user import User
from app.modules.recommendation.service import recommendation_service

router = APIRouter()


class RecommendedTopicOut(BaseModel):
    topic_slug: str
    topic_name: str
    topic_description: str | None
    difficulty: str
    estimated_hours: float
    score: float
    reasons: list[str]
    all_prereqs_met: bool


@router.get("", response_model=list[RecommendedTopicOut])
async def get_recommendations(
    request: Request,
    limit: int = Query(default=6, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
):
    """
    Get personalized topic recommendations for the authenticated user.
    Combines prerequisite graph traversal, difficulty alignment, and goal matching.
    """
    user: User = await get_current_user(request, db)
    recommendations = await recommendation_service.get_recommendations(
        db=db, user=user, limit=limit
    )
    return [
        RecommendedTopicOut(
            topic_slug=r.topic.slug,
            topic_name=r.topic.name,
            topic_description=r.topic.description,
            difficulty=r.topic.difficulty,
            estimated_hours=r.topic.estimated_hours,
            score=r.score,
            reasons=r.reasons,
            all_prereqs_met=r.all_prereqs_met,
        )
        for r in recommendations
    ]
