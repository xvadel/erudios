from __future__ import annotations

import uuid
from datetime import datetime, date

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Resource(Base):
    __tablename__ = "resources"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    topic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("topics.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    url: Mapped[str] = mapped_column(String(2048), nullable=False, unique=True)
    source_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # blog | github | paper | video | book | course | documentation
    author: Mapped[str | None] = mapped_column(String(255), nullable=True)
    published_at: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Quality & trust
    trust_score: Mapped[float] = mapped_column(Float, nullable=False, default=50.0)
    quality_score: Mapped[float] = mapped_column(Float, nullable=False, default=50.0)
    composite_score: Mapped[float] = mapped_column(Float, nullable=False, default=50.0)
    feedback_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    feedback_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Health
    is_alive: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_checked: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Rich metadata (stars, citations, views, etc.)
    resource_metadata: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    topic: Mapped["Topic"] = relationship(back_populates="resources")

    def __repr__(self) -> str:
        return f"<Resource title={self.title[:50]} score={self.composite_score:.1f}>"


class TrustedDomain(Base):
    __tablename__ = "trusted_domains"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    domain: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    base_trust_score: Mapped[float] = mapped_column(Float, nullable=False, default=80.0)
    category: Mapped[str] = mapped_column(
        String(100), nullable=False
    )  # official_docs | academic | blog | course | github
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class ResourceRefreshLog(Base):
    __tablename__ = "resource_refresh_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    topic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("topics.id", ondelete="CASCADE"), nullable=False, index=True
    )
    new_resources_found: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    stale_resources_flagged: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    dead_links_removed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    refreshed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    topic: Mapped["Topic"] = relationship(back_populates="refresh_logs")
