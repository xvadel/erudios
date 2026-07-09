from __future__ import annotations

import uuid
from datetime import date
from pydantic import BaseModel


class ResourceOut(BaseModel):
    id: uuid.UUID
    title: str
    url: str
    source_type: str
    author: str | None
    published_at: date | None
    trust_score: float
    quality_score: float
    composite_score: float

    model_config = {"from_attributes": True}
