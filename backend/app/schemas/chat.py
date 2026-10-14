from __future__ import annotations

import uuid
from datetime import datetime
from pydantic import BaseModel


class ChatSessionCreate(BaseModel):
    topic_slug: str


class ChatMessageCreate(BaseModel):
    content: str


class ChatMessageOut(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    role: str  # "user" | "assistant"
    content: str
    sources: list[dict]
    tokens_used: int
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatSessionOut(BaseModel):
    id: uuid.UUID
    topic_slug: str
    topic_name: str
    message_count: int
    created_at: datetime
