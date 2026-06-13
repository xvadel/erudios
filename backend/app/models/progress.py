from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class LearningProgress(Base):
    __tablename__ = "learning_progress"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    module_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("modules.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    mastery_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    quizzes_taken: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    avg_quiz_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    time_spent_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sections_completed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    last_reviewed: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_review: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )  # Spaced repetition

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="progress")
    module: Mapped["Module"] = relationship(back_populates="progress")
