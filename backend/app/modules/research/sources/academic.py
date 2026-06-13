from __future__ import annotations

from datetime import date

import structlog
import httpx

from app.modules.research.sources.base import ResourceSource, RawResource

log = structlog.get_logger()

OPENALEX_API = "https://api.openalex.org"


class OpenAlexSource(ResourceSource):
    """
    Discovers academic papers via OpenAlex API.
    Completely free — no API key required.
    """

    @property
    def source_type(self) -> str:
        return "paper"

    async def discover(self, topic: str, limit: int = 10) -> list[RawResource]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(
                    f"{OPENALEX_API}/works",
                    params={
                        "search": topic,
                        "filter": "has_oa_url:true",   # Open access only
                        "sort": "cited_by_count:desc",
                        "per_page": limit,
                        "mailto": "contact@erudios.io",   # Polite pool
                    },
                )
                response.raise_for_status()
                data = response.json()
            except Exception as exc:
                log.error("OpenAlex search failed", topic=topic, error=str(exc))
                return []

        results = []
        for work in data.get("results", []):
            # Prefer open access PDF URL
            url = (
                work.get("open_access", {}).get("oa_url")
                or work.get("primary_location", {}).get("landing_page_url")
            )
            if not url:
                continue

            pub_year = work.get("publication_year")
            published = date(pub_year, 1, 1) if pub_year else None

            results.append(RawResource(
                title=work.get("title", ""),
                url=url,
                source_type="paper",
                published_at=published,
                description=work.get("abstract", ""),
                signals={
                    "citations": work.get("cited_by_count", 0),
                    "doi": work.get("doi"),
                    "open_access": work.get("open_access", {}).get("is_oa", False),
                },
            ))

        return results
