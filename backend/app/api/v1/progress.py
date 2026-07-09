from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.api.v1.auth import get_current_user
from app.models.user import User
from app.models.progress import LearningProgress
from app.models.curriculum import Module, Curriculum
from app.models.topic import Topic
from app.core.exceptions import NotFoundError, ForbiddenError
from app.schemas.progress import (
    CompleteModuleRequest, QuizResultRequest, ProgressOut, CurriculumProgressOut
)

router = APIRouter()


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_or_create_progress(
    db: AsyncSession, user_id: uuid.UUID, module_id: uuid.UUID
) -> LearningProgress:
    result = await db.execute(
        select(LearningProgress).where(
            LearningProgress.user_id == user_id,
            LearningProgress.module_id == module_id,
        )
    )
    progress = result.scalar_one_or_none()
    if not progress:
        progress = LearningProgress(user_id=user_id, module_id=module_id)
        db.add(progress)
        await db.flush()
    return progress


async def _verify_module_ownership(
    db: AsyncSession, user_id: uuid.UUID, module_id: uuid.UUID
) -> Module:
    """Ensure the module belongs to a curriculum owned by this user."""
    result = await db.execute(
        select(Module)
        .join(Curriculum, Module.curriculum_id == Curriculum.id)
        .where(
            Module.id == module_id,
            Curriculum.user_id == user_id,
        )
        .options(selectinload(Module.topic))
    )
    module = result.scalar_one_or_none()
    if not module:
        raise NotFoundError("Module not found or not in your curriculum")
    return module


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/modules/{module_id}/complete", response_model=ProgressOut)
async def complete_module(
    module_id: uuid.UUID,
    body: CompleteModuleRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Mark a module as completed. Sets mastery_score to 100 and records time spent.
    Safe to call multiple times — idempotent.
    """
    user: User = await get_current_user(request, db)
    module = await _verify_module_ownership(db, user.id, module_id)

    progress = await _get_or_create_progress(db, user.id, module_id)
    progress.mastery_score = 100.0
    progress.time_spent_minutes += body.time_spent_minutes
    progress.last_reviewed = datetime.now(timezone.utc)
    await db.flush()

    return ProgressOut(
        module_id=module_id,
        topic_slug=module.topic.slug if module.topic else "",
        mastery_score=progress.mastery_score,
        quizzes_taken=progress.quizzes_taken,
        avg_quiz_score=progress.avg_quiz_score,
        time_spent_minutes=progress.time_spent_minutes,
        sections_completed=progress.sections_completed,
        last_reviewed=progress.last_reviewed,
    )


@router.post("/modules/{module_id}/quiz-result", response_model=ProgressOut)
async def submit_quiz_result(
    module_id: uuid.UUID,
    body: QuizResultRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Record a quiz result for a module. Updates rolling average quiz score.
    """
    user: User = await get_current_user(request, db)
    module = await _verify_module_ownership(db, user.id, module_id)

    progress = await _get_or_create_progress(db, user.id, module_id)

    # Rolling average
    total = progress.avg_quiz_score * progress.quizzes_taken + body.score
    progress.quizzes_taken += 1
    progress.avg_quiz_score = round(total / progress.quizzes_taken, 1)
    progress.time_spent_minutes += body.time_spent_minutes
    progress.last_reviewed = datetime.now(timezone.utc)

    # Update mastery score: weighted 70% quiz, 30% prior mastery
    progress.mastery_score = round(
        progress.avg_quiz_score * 0.7 + progress.mastery_score * 0.3, 1
    )
    await db.flush()

    return ProgressOut(
        module_id=module_id,
        topic_slug=module.topic.slug if module.topic else "",
        mastery_score=progress.mastery_score,
        quizzes_taken=progress.quizzes_taken,
        avg_quiz_score=progress.avg_quiz_score,
        time_spent_minutes=progress.time_spent_minutes,
        sections_completed=progress.sections_completed,
        last_reviewed=progress.last_reviewed,
    )


@router.get("/curricula/{curriculum_id}", response_model=CurriculumProgressOut)
async def get_curriculum_progress(
    curriculum_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Get progress summary for all modules in a curriculum.
    Uses a single joined query to avoid N+1 topic lookups.
    """
    user: User = await get_current_user(request, db)

    # Verify ownership
    result = await db.execute(
        select(Curriculum).where(
            Curriculum.id == curriculum_id,
            Curriculum.user_id == user.id,
        )
    )
    curriculum = result.scalar_one_or_none()
    if not curriculum:
        raise NotFoundError("Curriculum not found")

    # Load all modules with their topics in one query
    modules_result = await db.execute(
        select(Module)
        .where(Module.curriculum_id == curriculum_id)
        .options(selectinload(Module.topic))
        .order_by(Module.order_index)
    )
    modules = list(modules_result.scalars().all())

    # Load all progress rows for these modules in one query
    module_ids = [m.id for m in modules]
    if module_ids:
        progress_result = await db.execute(
            select(LearningProgress).where(
                LearningProgress.user_id == user.id,
                LearningProgress.module_id.in_(module_ids),
            )
        )
        progress_map = {p.module_id: p for p in progress_result.scalars().all()}
    else:
        progress_map = {}

    progress_list = []
    completed = 0

    for module in modules:
        p = progress_map.get(module.id)
        mastery = p.mastery_score if p else 0.0
        if mastery >= 80.0:
            completed += 1

        progress_list.append(
            ProgressOut(
                module_id=module.id,
                topic_slug=module.topic.slug if module.topic else "",
                mastery_score=mastery,
                quizzes_taken=p.quizzes_taken if p else 0,
                avg_quiz_score=p.avg_quiz_score if p else 0.0,
                time_spent_minutes=p.time_spent_minutes if p else 0,
                sections_completed=p.sections_completed if p else 0,
                last_reviewed=p.last_reviewed if p else None,
            )
        )

    total = len(modules)
    return CurriculumProgressOut(
        curriculum_id=curriculum_id,
        total_modules=total,
        completed_modules=completed,
        completion_pct=round(completed / total * 100, 1) if total > 0 else 0.0,
        progress=progress_list,
    )
