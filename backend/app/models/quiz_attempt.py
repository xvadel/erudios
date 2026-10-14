from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    quiz_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    module_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("modules.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Selected option indices: [0, 2, 1, 3, ...]
    answers_given: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    time_taken_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    difficulty_level: Mapped[str] = mapped_column(String(50), nullable=False, default="intermediate")
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship()
    quiz: Mapped["Quiz"] = relationship()
    module: Mapped["Module"] = relationship()
