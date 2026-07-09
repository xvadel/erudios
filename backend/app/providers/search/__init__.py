"""
Search provider package.

Provides a unified SearchProvider interface over multiple web/academic search backends.
Use get_search_providers() to get configured providers in priority order.
"""
from app.providers.search.base import SearchProvider, RawResource
from app.providers.search.duckduckgo import DuckDuckGoSearchProvider
from app.providers.search.tavily import TavilySearchProvider

__all__ = [
    "SearchProvider",
    "RawResource",
    "DuckDuckGoSearchProvider",
    "TavilySearchProvider",
    "get_search_providers",
]


def get_search_providers() -> list[SearchProvider]:
    """Return configured search providers in priority order (best quality first)."""
    from app.config import settings
    providers: list[SearchProvider] = []
    if settings.has_tavily:
        try:
            providers.append(TavilySearchProvider())
        except RuntimeError:
            pass
    providers.append(DuckDuckGoSearchProvider())
    return providers
