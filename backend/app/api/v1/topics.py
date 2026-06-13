from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.modules.topic_graph.service import topic_graph_service
from app.models.topic import Topic

router = APIRouter()


# ── Schemas ───────────────────────────────────────────────────────────────────

class TopicOut(BaseModel):
    id: uuid.UUID
    slug: str
    name: str
    description: str | None
    difficulty: str
    estimated_hours: float
    parent_slug: str | None = None
    child_count: int = 0

    model_config = {"from_attributes": True}


class TopicTreeNode(BaseModel):
    topic: TopicOut
    children: list["TopicTreeNode"] = []


class DependencyOut(BaseModel):
    topic: TopicOut
    reason: str | None


class WhatsNextResponse(BaseModel):
    completed_topic: str
    next_steps: list[dict]
    message: str


def _topic_to_out(t: Topic) -> TopicOut:
    return TopicOut(
        id=t.id,
        slug=t.slug,
        name=t.name,
        description=t.description,
        difficulty=t.difficulty,
        estimated_hours=t.estimated_hours,
        parent_slug=None,   # Resolved separately if needed
        child_count=len(t.children) if t.children else 0,
    )


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("", response_model=list[TopicOut])
async def list_root_topics(db: AsyncSession = Depends(get_db)):
    """List all top-level AI domains (no LLM cost — pre-built data)."""
    roots = await topic_graph_service.get_all_roots(db)
    return [_topic_to_out(t) for t in roots]


@router.get("/search", response_model=list[TopicOut])
async def search_topics(
    q: str = Query(..., min_length=2),
    db: AsyncSession = Depends(get_db),
):
    """Search topics by name/description (no LLM cost)."""
    results = await topic_graph_service.search(db, q)
    return [_topic_to_out(t) for t in results]


@router.get("/{slug}", response_model=TopicOut)
async def get_topic(slug: str, db: AsyncSession = Depends(get_db)):
    """Get a topic by slug with its dependencies (no LLM cost)."""
    topic = await topic_graph_service.get_by_slug(db, slug)
    return _topic_to_out(topic)


@router.get("/{slug}/children", response_model=list[TopicOut])
async def get_children(slug: str, db: AsyncSession = Depends(get_db)):
    """Get direct sub-topics of a topic (no LLM cost)."""
    children = await topic_graph_service.get_children(db, slug)
    return [_topic_to_out(t) for t in children]


@router.get("/{slug}/prerequisites", response_model=list[DependencyOut])
async def get_prerequisites(slug: str, db: AsyncSession = Depends(get_db)):
    """Get prerequisite topics with explanations (no LLM cost)."""
    prereqs = await topic_graph_service.get_prerequisites(db, slug)
    return [
        DependencyOut(topic=_topic_to_out(p["topic"]), reason=p["reason"])
        for p in prereqs
    ]


@router.get("/{slug}/whats-next", response_model=WhatsNextResponse)
async def whats_next(
    slug: str,
    completed: str | None = Query(
        None,
        description="Comma-separated list of completed topic slugs"
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    The core 'What should I learn next?' endpoint.
    Returns unlocked topics with reasons. Zero LLM cost — pure graph traversal.
    """
    completed_slugs = [s.strip() for s in completed.split(",")] if completed else []
    if slug not in completed_slugs:
        completed_slugs.append(slug)

    recommendations = await topic_graph_service.get_whats_next(db, slug, completed_slugs)

    next_steps = [
        {
            "topic": _topic_to_out(r["topic"]).model_dump(),
            "reason": r["reason"],
            "readiness": r["readiness"],
        }
        for r in recommendations
    ]

    if next_steps:
        first = next_steps[0]["topic"]["name"]
        message = (
            f"You've completed '{slug.replace('-', ' ').title()}'. "
            f"Your next recommended topic is **{first}**."
        )
    else:
        message = (
            f"Great work completing '{slug.replace('-', ' ').title()}'! "
            "No immediate next steps — you may have covered all related topics."
        )

    return WhatsNextResponse(
        completed_topic=slug,
        next_steps=next_steps,
        message=message,
    )


@router.get("/{slug}/learning-path", response_model=list[TopicOut])
async def get_learning_path(slug: str, db: AsyncSession = Depends(get_db)):
    """
    Get the topologically sorted learning path for all topics under a root.
    Zero LLM cost — Kahn's algorithm on pre-built dependency graph.
    """
    path = await topic_graph_service.get_learning_path(db, slug)
    return [_topic_to_out(t) for t in path]
