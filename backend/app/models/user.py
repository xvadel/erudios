from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # OAuth
    oauth_provider: Mapped[str] = mapped_column(String(50), nullable=False)  # "google" | "github"
    oauth_id: Mapped[str] = mapped_column(String(255), nullable=False)

    # Learning preferences
    level: Mapped[str] = mapped_column(
        String(50), nullable=False, default="beginner"
    )  # beginner | intermediate | advanced
    learning_style: Mapped[str] = mapped_column(
        String(50), nullable=False, default="practical"
    )  # visual | practical | research | interview | project
    goal: Mapped[str] = mapped_column(
        String(50), nullable=False, default="general"
    )  # job | research | startup | academic | general

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    curricula: Mapped[list["Curriculum"]] = relationship(back_populates="user", lazy="select")
    progress: Mapped[list["LearningProgress"]] = relationship(back_populates="user", lazy="select")
    chat_sessions: Mapped[list["ChatSession"]] = relationship(back_populates="user", lazy="select")

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email}>"
