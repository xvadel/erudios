from __future__ import annotations

import structlog
from tavily import TavilyClient

from app.providers.search.base import SearchProvider, RawResource
from app.config import settings

log = structlog.get_logger()


class TavilySearchProvider(SearchProvider):
    """Premium search via Tavily API. Requires TAVILY_API_KEY."""

    def __init__(self) -> None:
        if not settings.TAVILY_API_KEY:
            raise RuntimeError("TAVILY_API_KEY is not configured")
        self._client = TavilyClient(api_key=settings.TAVILY_API_KEY)

    @property
    def provider_name(self) -> str:
        return "tavily"

    async def search(self, query: str, limit: int = 10) -> list[RawResource]:
        results: list[RawResource] = []
        try:
            response = self._client.search(
                query=query,
                max_results=limit,
                include_answer=False,
                search_depth="advanced",
            )
            for r in response.get("results", []):
                results.append(
                    RawResource(
                        title=r.get("title", ""),
                        url=r.get("url", ""),
                        source_type=self._classify_url(r.get("url", "")),
                        snippet=r.get("content"),
                        signals={
                            "source": "tavily",
                            "relevance_score": r.get("score", 0.0),
                        },
                    )
                )
        except Exception as exc:
            log.warning("Tavily search failed", query=query, error=str(exc))
        return results

    @staticmethod
    def _classify_url(url: str) -> str:
        url = url.lower()
        if "github.com" in url:
            return "github"
        if "arxiv.org" in url or "semanticscholar" in url or "openreview" in url:
            return "paper"
        if "youtube.com" in url or "youtu.be" in url:
            return "video"
        if "docs." in url or "/documentation" in url or "readthedocs" in url:
            return "documentation"
        if "coursera" in url or "udemy" in url or "edx.org" in url or "fast.ai" in url:
            return "course"
        return "blog"
