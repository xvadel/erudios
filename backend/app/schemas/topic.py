from __future__ import annotations

import uuid
from pydantic import BaseModel


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
