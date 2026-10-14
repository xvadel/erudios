from __future__ import annotations

import structlog
from duckduckgo_search import DDGS

from app.providers.search.base import SearchProvider, RawResource

log = structlog.get_logger()


class DuckDuckGoSearchProvider(SearchProvider):
    """Free web search via DuckDuckGo. No API key required."""

    @property
    def provider_name(self) -> str:
        return "duckduckgo"

    async def search(self, query: str, limit: int = 10) -> list[RawResource]:
        results: list[RawResource] = []
        try:
            with DDGS() as ddgs:
                for r in ddgs.text(f"{query} tutorial site:github.com OR site:arxiv.org OR site:medium.com", max_results=limit):
                    results.append(
                        RawResource(
                            title=r.get("title", ""),
                            url=r.get("href", ""),
                            source_type=self._classify_url(r.get("href", "")),
                            snippet=r.get("body"),
                            signals={"source": "duckduckgo"},
                        )
                    )
        except Exception as exc:
            log.warning("DuckDuckGo search failed", query=query, error=str(exc))
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
