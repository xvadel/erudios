from __future__ import annotations

import uuid
from datetime import datetime
from pydantic import BaseModel


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
