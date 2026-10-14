from __future__ import annotations

from datetime import date, timedelta
from urllib.parse import urlparse

import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.modules.research.sources.base import RawResource
from app.models.resource import TrustedDomain
from app.config import settings

log = structlog.get_logger()

# Recency thresholds
NOW = date.today()
VERY_RECENT = 365       # < 1 year
RECENT = 365 * 2        # 1–2 years
OLDER = 365 * 4         # 2–4 years
# Older than 4 years = 0 recency score (stale for fast-moving AI field)


class ResourceRanker:
    """
    Computes composite trust + quality score for each resource.

    Score weights:
    - Source authority (trusted domain match):  25%
    - Recency:                                  20%
    - Community signals (stars, citations):     20%
    - Content depth (title/description length): 20%
    - Link type bonus (paper > github > blog):  15%
    """

    def __init__(self, trusted_domains: dict[str, float]):
        """
        trusted_domains: {domain: base_trust_score}
        """
        self._trusted = trusted_domains

    def _authority_score(self, url: str) -> float:
        """Score based on domain trust."""
        try:
            host = urlparse(url).netloc.lower()
            # Remove www.
            host = host.removeprefix("www.")
            # Exact match
            if host in self._trusted:
                return self._trusted[host]
            # Check parent domains (e.g. username.github.io → github.io)
            parts = host.split(".")
            for i in range(1, len(parts)):
                parent = ".".join(parts[i:])
                if parent in self._trusted:
                    return self._trusted[parent] * 0.9  # Slight discount for subdomains
        except Exception:
            pass
        return 40.0  # Unknown domain — below minimum but not excluded yet

    def _recency_score(self, published_at: date | None) -> float:
        if published_at is None:
            return 50.0  # Unknown date — neutral
        age_days = (NOW - published_at).days
        if age_days < 0:
            return 80.0  # Future date — treat as recent
        if age_days <= VERY_RECENT:
            return 100.0
        if age_days <= RECENT:
            return 75.0
        if age_days <= OLDER:
            return 50.0
        return 20.0

    def _community_score(self, signals: dict, source_type: str) -> float:
        if source_type == "github":
            stars = signals.get("stars", 0)
            if stars >= 5000:
                return 100.0
            if stars >= 1000:
                return 80.0
            if stars >= 200:
                return 60.0
            if stars >= 50:
                return 40.0
            return 20.0

        if source_type == "paper":
            citations = signals.get("citations", 0)
            if citations >= 500:
                return 100.0
            if citations >= 100:
                return 80.0
            if citations >= 20:
                return 60.0
            if citations >= 5:
                return 40.0
            return 30.0

        # Blog/course — use Tavily relevance score if available
        tavily_score = signals.get("score", 0)
        if tavily_score:
            return tavily_score * 100

        return 50.0

    def _depth_score(self, resource: RawResource) -> float:
        """Estimate content depth from available metadata."""
        title_len = len(resource.title)
        desc_len = len(resource.description or "")

        # More descriptive = likely more in-depth
        score = 50.0
        if desc_len > 300:
            score += 20
        elif desc_len > 100:
            score += 10
        if title_len > 30:
            score += 10
        # Penalize very short titles (likely spam/low quality)
        if title_len < 10:
            score -= 20
        return min(100.0, max(0.0, score))

    def _type_bonus(self, source_type: str) -> float:
        """Small bonus based on source type reliability."""
        bonuses = {
            "paper": 15.0,
            "documentation": 15.0,
            "course": 12.0,
            "github": 10.0,
            "book": 10.0,
            "video": 5.0,
            "blog": 0.0,
        }
        return bonuses.get(source_type, 0.0)

    def compute_score(self, resource: RawResource) -> tuple[float, float, float]:
        """
        Returns (trust_score, quality_score, composite_score).
        """
        authority = self._authority_score(resource.url)
        recency = self._recency_score(resource.published_at)
        community = self._community_score(resource.signals, resource.source_type)
        depth = self._depth_score(resource)
        type_b = self._type_bonus(resource.source_type)

        # Weighted composite
        composite = (
            authority * 0.25
            + recency * 0.20
            + community * 0.20
            + depth * 0.20
            + type_b * 0.15  # Note: type bonus is not * 0.15 of 100, it's a direct add
        )

        # Simpler: authority is the trust signal, rest is quality
        trust = authority
        quality = (recency * 0.3 + community * 0.4 + depth * 0.3)

        return round(trust, 1), round(quality, 1), round(composite, 1)

    def rank(self, resources: list[RawResource]) -> list[tuple[RawResource, float, float, float]]:
        """Sort resources by composite score, filter below minimum trust."""
        scored = []
        for r in resources:
            trust, quality, composite = self.compute_score(r)
            if trust >= settings.MIN_RESOURCE_TRUST_SCORE or composite >= 40:
                scored.append((r, trust, quality, composite))

        scored.sort(key=lambda x: x[3], reverse=True)
        return scored


async def build_ranker(db: AsyncSession) -> ResourceRanker:
    """Build a ResourceRanker with current trusted domain scores from DB."""
    result = await db.execute(select(TrustedDomain))
    domains = result.scalars().all()
    trusted = {d.domain: d.base_trust_score for d in domains}
    return ResourceRanker(trusted_domains=trusted)
