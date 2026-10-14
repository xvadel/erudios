from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date


@dataclass
class RawResource:
    """Normalized resource discovered from any search source."""
    title: str
    url: str
    source_type: str  # blog | github | paper | video | course | documentation | book
    author: str | None = None
    published_at: date | None = None
    snippet: str | None = None  # Short description/abstract
    signals: dict = field(default_factory=dict)  # Stars, citations, views, etc.


class SearchProvider(ABC):
    """Abstract base for all web/academic search providers."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Human-readable name of this provider."""
        ...

    @abstractmethod
    async def search(self, query: str, limit: int = 10) -> list[RawResource]:
        """
        Search for resources matching the query.
        Returns up to `limit` results as normalized RawResource objects.
        """
        ...

    async def is_available(self) -> bool:
        """Check if this provider is configured and reachable. Override if needed."""
        return True
