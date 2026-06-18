from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.artifact import ArtifactShell
    from app.models.chat import ChatSession
    from app.models.curriculum import Curriculum
    from app.models.resource import Resource, ResourceRefreshLog


class Topic(Base):
    __tablename__ = "topics"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("topics.id", ondelete="SET NULL"), nullable=True, index=True
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    difficulty: Mapped[str] = mapped_column(String(50), nullable=False, default="intermediate")
    estimated_hours: Mapped[float] = mapped_column(nullable=False, default=2.0)
    is_seed: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, default=dict)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Self-referential hierarchy
    parent: Mapped["Topic | None"] = relationship(
        "Topic", remote_side="Topic.id", back_populates="children", lazy="select"
    )
    children: Mapped[list["Topic"]] = relationship(
        "Topic", back_populates="parent", lazy="selectin"
    )

    # Prerequisite relationships
    prerequisites: Mapped[list["TopicDependency"]] = relationship(
        "TopicDependency",
        foreign_keys="TopicDependency.dependent_id",
        back_populates="dependent",
        lazy="select",
    )
    dependents: Mapped[list["TopicDependency"]] = relationship(
        "TopicDependency",
        foreign_keys="TopicDependency.prerequisite_id",
        back_populates="prerequisite",
        lazy="select",
    )

    # Other relationships
    resources: Mapped[list["Resource"]] = relationship(back_populates="topic", lazy="select")
    curricula: Mapped[list["Curriculum"]] = relationship(back_populates="root_topic", lazy="select")
    artifact_shell: Mapped["ArtifactShell | None"] = relationship(
        back_populates="topic", lazy="select", uselist=False
    )
    refresh_logs: Mapped[list["ResourceRefreshLog"]] = relationship(
        back_populates="topic", lazy="select"
    )
    chat_sessions: Mapped[list["ChatSession"]] = relationship(
        back_populates="topic", lazy="select"
    )

    def __repr__(self) -> str:
        return f"<Topic slug={self.slug}>"


class TopicDependency(Base):
    __tablename__ = "topic_dependencies"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    prerequisite_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("topics.id", ondelete="CASCADE"), nullable=False, index=True
    )
    dependent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("topics.id", ondelete="CASCADE"), nullable=False, index=True
    )
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    prerequisite: Mapped["Topic"] = relationship(
        "Topic", foreign_keys=[prerequisite_id], back_populates="dependents"
    )
    dependent: Mapped["Topic"] = relationship(
        "Topic", foreign_keys=[dependent_id], back_populates="prerequisites"
    )

    def __repr__(self) -> str:
        return f"<TopicDependency {self.prerequisite_id} → {self.dependent_id}>"
