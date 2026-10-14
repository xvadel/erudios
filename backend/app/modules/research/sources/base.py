from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date


@dataclass
class RawResource:
    """Unified resource representation from any source."""
    title: str
    url: str
    source_type: str           # blog | github | paper | video | book | course | documentation
    author: str | None = None
    published_at: date | None = None
    description: str | None = None
    # Source-specific signals for ranking
    signals: dict = field(default_factory=dict)
    # e.g. {"stars": 1200, "citations": 45, "views": 50000}


class ResourceSource(ABC):
    """Abstract base class for resource discovery sources (Strategy pattern)."""

    @property
    @abstractmethod
    def source_type(self) -> str:
        """Return the source type identifier."""
        ...

    @abstractmethod
    async def discover(self, topic: str, limit: int = 10) -> list[RawResource]:
        """Discover resources for the given topic."""
        ...

    @property
    def is_available(self) -> bool:
        """Return True if the required API keys/credentials are configured."""
        return True
