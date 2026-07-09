from __future__ import annotations

import uuid
from datetime import datetime
from pydantic import BaseModel, Field


class CompleteModuleRequest(BaseModel):
    time_spent_minutes: int = Field(default=0, ge=0)


class QuizResultRequest(BaseModel):
    score: float = Field(..., ge=0.0, le=100.0, description="Quiz score as percentage 0–100")
    time_spent_minutes: int = Field(default=0, ge=0)


class ProgressOut(BaseModel):
    module_id: uuid.UUID
    topic_slug: str
    mastery_score: float
    quizzes_taken: int
    avg_quiz_score: float
    time_spent_minutes: int
    sections_completed: int
    last_reviewed: datetime | None

    model_config = {"from_attributes": True}


class CurriculumProgressOut(BaseModel):
    curriculum_id: uuid.UUID
    total_modules: int
    completed_modules: int
    completion_pct: float
    progress: list[ProgressOut]
