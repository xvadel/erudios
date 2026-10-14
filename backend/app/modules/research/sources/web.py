from __future__ import annotations

import structlog
from duckduckgo_search import DDGS

from app.modules.research.sources.base import ResourceSource, RawResource
from app.config import settings

log = structlog.get_logger()


class DuckDuckGoSource(ResourceSource):
    """
    Free web search via DuckDuckGo — no API key required.
    Default search source when Tavily is not configured.
    """

    @property
    def source_type(self) -> str:
        return "blog"

    async def discover(self, topic: str, limit: int = 10) -> list[RawResource]:
        results = []
        queries = [
            f"{topic} tutorial guide",
            f"{topic} explained deep dive",
            f"learn {topic} best resources",
        ]

        seen_urls = set()
        with DDGS() as ddgs:
            for query in queries:
                try:
                    search_results = list(ddgs.text(
                        query,
                        max_results=limit // len(queries) + 2,
                        safesearch="moderate",
                    ))
                    for r in search_results:
                        url = r.get("href", "")
                        if not url or url in seen_urls:
                            continue
                        seen_urls.add(url)
                        results.append(RawResource(
                            title=r.get("title", ""),
                            url=url,
                            source_type="blog",
                            description=r.get("body", ""),
                        ))
                except Exception as exc:
                    log.warning("DuckDuckGo search error", query=query, error=str(exc))

        return results[:limit]


class TavilySource(ResourceSource):
    """
    Tavily search API — higher quality results, 1000 free searches/month.
    Optional — requires TAVILY_API_KEY.
    """

    @property
    def source_type(self) -> str:
        return "blog"

    @property
    def is_available(self) -> bool:
        return settings.has_tavily

    async def discover(self, topic: str, limit: int = 10) -> list[RawResource]:
        if not settings.has_tavily:
            log.warning("Tavily not configured, skipping")
            return []

        try:
            from tavily import TavilyClient
            client = TavilyClient(api_key=settings.TAVILY_API_KEY)

            response = client.search(
                query=f"{topic} machine learning tutorial guide",
                search_depth="advanced",
                max_results=limit,
                include_raw_content=False,
            )

            results = []
            for r in response.get("results", []):
                results.append(RawResource(
                    title=r.get("title", ""),
                    url=r.get("url", ""),
                    source_type="blog",
                    description=r.get("content", ""),
                    signals={"score": r.get("score", 0.5)},
                ))
            return results

        except Exception as exc:
            log.error("Tavily search failed", topic=topic, error=str(exc))
            return []
