from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ArtifactShell(Base):
    """
    The 'skeleton' of a learning artifact for a topic.
    Contains overview and section titles — generated cheaply (~200 tokens).
    Shared across ALL users (not per-user).
    """

    __tablename__ = "artifact_shells"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    topic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("topics.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    overview: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Ordered list of section slugs: ["introduction", "deep-dive", "examples", ...]
    section_titles: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    cache_key: Mapped[str] = mapped_column(String(512), nullable=False, unique=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    topic: Mapped["Topic"] = relationship(back_populates="artifact_shell")
    sections: Mapped[list["ArtifactSection"]] = relationship(
        back_populates="shell", cascade="all, delete-orphan", lazy="select"
    )

    def __repr__(self) -> str:
        return f"<ArtifactShell topic={self.topic_id}>"


class ArtifactSection(Base):
    """
    One lazily-generated section of a learning artifact.
    base_content is shared across users.
    style_overlays adds style-specific additions per learning style.
    """

    __tablename__ = "artifact_sections"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    shell_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("artifact_shells.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    section_slug: Mapped[str] = mapped_column(String(255), nullable=False)
    section_title: Mapped[str] = mapped_column(String(512), nullable=False)
    base_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    # { "visual": "...", "practical": "...", "research": "...", "interview": "..." }
    style_overlays: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    cache_key: Mapped[str] = mapped_column(String(512), nullable=False, unique=True)
    order_index: Mapped[int] = mapped_column(nullable=False, default=0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    shell: Mapped["ArtifactShell"] = relationship(back_populates="sections")
    quiz: Mapped["Quiz | None"] = relationship(
        back_populates="section", lazy="select", uselist=False
    )

    def __repr__(self) -> str:
        return f"<ArtifactSection slug={self.section_slug}>"


class Quiz(Base):
    """Quiz questions for one artifact section. Shared across users."""

    __tablename__ = "quizzes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    section_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("artifact_sections.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    # Array of { question, options: [], correct_index, explanation }
    questions: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    cache_key: Mapped[str] = mapped_column(String(512), nullable=False, unique=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    section: Mapped["ArtifactSection"] = relationship(back_populates="quiz")
