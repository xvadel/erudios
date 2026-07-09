from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.api.v1.auth import get_current_user
from app.models.user import User
from app.modules.intelligence.service import (
    learning_intelligence_service,
    DailyPlan,
    ReviewItem,
)

router = APIRouter()


@router.get("/daily-plan", response_model=DailyPlan)
async def get_daily_plan(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Synthesize and retrieve today's personalized daily plan, containing spaced
    repetition reviews, recommendations, weaknesses, and a motivational brief.
    """
    user: User = await get_current_user(request, db)
    return await learning_intelligence_service.get_daily_plan(db, user)


@router.get("/review-queue", response_model=list[ReviewItem])
async def get_review_queue(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieve user modules currently due or overdue for a spaced repetition review.
    """
    user: User = await get_current_user(request, db)
    return await learning_intelligence_service.get_review_queue(db, user.id)
