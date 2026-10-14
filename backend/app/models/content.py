from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class GeneratedContent(Base):
    """
    Permanent shared cache for all LLM-generated content.
    Key format: "{topic_slug}/{section_slug}/{content_type}"
    Examples:
      - "rag/chunking/base_content"
      - "rag/chunking/quiz"
      - "rag/chunking/style_visual"
      - "rag/shell"
    """

    __tablename__ = "generated_content"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    cache_key: Mapped[str] = mapped_column(
        String(512), nullable=False, unique=True, index=True
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    provider_used: Mapped[str] = mapped_column(String(100), nullable=False)
    model_used: Mapped[str] = mapped_column(String(100), nullable=False)
    tokens_input: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tokens_output: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    def __repr__(self) -> str:
        return f"<GeneratedContent key={self.cache_key}>"
