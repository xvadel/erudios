from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Curriculum(Base):
    __tablename__ = "curricula"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    root_topic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("topics.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # User profile at time of generation (may differ from current profile)
    level: Mapped[str] = mapped_column(String(50), nullable=False)
    learning_style: Mapped[str] = mapped_column(String(50), nullable=False)
    goal: Mapped[str] = mapped_column(String(50), nullable=False)

    # Ordered list of module IDs (can be reordered by user)
    module_order: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)

    # Cache key for this curriculum profile (topic+level+style+goal)
    cache_key: Mapped[str] = mapped_column(String(512), nullable=False, index=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="curricula")
    root_topic: Mapped["Topic"] = relationship(back_populates="curricula")
    modules: Mapped[list["Module"]] = relationship(
        back_populates="curriculum", cascade="all, delete-orphan", lazy="select"
    )

    def __repr__(self) -> str:
        return f"<Curriculum id={self.id} topic={self.root_topic_id}>"


class Module(Base):
    __tablename__ = "modules"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    curriculum_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("curricula.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    topic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("topics.id", ondelete="CASCADE"), nullable=False, index=True
    )
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    why_next: Mapped[str | None] = mapped_column(Text, nullable=True)  # "Why this comes after X"
    estimated_hours: Mapped[float] = mapped_column(Float, nullable=False, default=2.0)
    difficulty: Mapped[str] = mapped_column(String(50), nullable=False, default="intermediate")

    curriculum: Mapped["Curriculum"] = relationship(back_populates="modules")
    topic: Mapped["Topic"] = relationship(lazy="joined")
    progress: Mapped[list["LearningProgress"]] = relationship(
        back_populates="module", lazy="select"
    )

    def __repr__(self) -> str:
        return f"<Module order={self.order_index} title={self.title[:40]}>"
