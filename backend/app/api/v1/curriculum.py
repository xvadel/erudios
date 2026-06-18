from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.api.v1.auth import get_current_user
from app.models.user import User
from app.models.curriculum import Curriculum, Module
from app.modules.curriculum.service import curriculum_service
from app.core.exceptions import ForbiddenError

router = APIRouter()


# ── Schemas ───────────────────────────────────────────────────────────────────

class ModuleOut(BaseModel):
    id: uuid.UUID
    order_index: int
    title: str
    description: str | None
    why_next: str | None
    estimated_hours: float
    difficulty: str
    topic_slug: str
    topic_name: str

    model_config = {"from_attributes": True}


class CurriculumOut(BaseModel):
    id: uuid.UUID
    topic_slug: str
    topic_name: str
    level: str
    learning_style: str
    goal: str
    modules: list[ModuleOut]
    created_at: datetime

    model_config = {"from_attributes": True}


class CurriculumSummary(BaseModel):
    id: uuid.UUID
    topic_slug: str
    topic_name: str
    level: str
    learning_style: str
    goal: str
    module_count: int
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _module_to_out(m: Module) -> ModuleOut:
    return ModuleOut(
        id=m.id,
        order_index=m.order_index,
        title=m.title,
        description=m.description,
        why_next=m.why_next,
        estimated_hours=m.estimated_hours,
        difficulty=m.difficulty,
        topic_slug=m.topic.slug,
        topic_name=m.topic.name,
    )


def _curriculum_to_out(c: Curriculum) -> CurriculumOut:
    sorted_modules = sorted(c.modules, key=lambda m: m.order_index)
    return CurriculumOut(
        id=c.id,
        topic_slug=c.root_topic.slug,
        topic_name=c.root_topic.name,
        level=c.level,
        learning_style=c.learning_style,
        goal=c.goal,
        modules=[_module_to_out(m) for m in sorted_modules],
        created_at=c.created_at,
    )


def _curriculum_to_summary(c: Curriculum) -> CurriculumSummary:
    return CurriculumSummary(
        id=c.id,
        topic_slug=c.root_topic.slug,
        topic_name=c.root_topic.name,
        level=c.level,
        learning_style=c.learning_style,
        goal=c.goal,
        module_count=len(c.modules),
        created_at=c.created_at,
    )


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/{topic_slug}", response_model=CurriculumOut)
async def create_curriculum(
    topic_slug: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Generate (or return cached) a personalized curriculum for a topic.
    Uses the user's current level, learning_style, and goal profile.
    First call triggers LLM generation (~2–4 s).
    Subsequent calls with the same profile return instantly from cache.
    """
    user: User = await get_current_user(request, db)
    curriculum = await curriculum_service.get_or_create(db, user, topic_slug)
    return _curriculum_to_out(curriculum)


@router.get("/me", response_model=list[CurriculumSummary])
async def list_my_curricula(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """List all curricula belonging to the authenticated user."""
    user: User = await get_current_user(request, db)
    curricula = await curriculum_service.list_for_user(db, user.id)
    return [_curriculum_to_summary(c) for c in curricula]


@router.get("/{curriculum_id}", response_model=CurriculumOut)
async def get_curriculum(
    curriculum_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Fetch a curriculum by ID (must belong to authenticated user)."""
    user: User = await get_current_user(request, db)
    curriculum = await curriculum_service.get_by_id(db, curriculum_id)
    if curriculum.user_id != user.id:
        raise ForbiddenError("This curriculum does not belong to you")
    return _curriculum_to_out(curriculum)


@router.delete("/{curriculum_id}", status_code=204)
async def delete_curriculum(
    curriculum_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Delete a curriculum (only the owner can delete)."""
    user: User = await get_current_user(request, db)
    await curriculum_service.delete(db, curriculum_id, user.id)
