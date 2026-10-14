from __future__ import annotations

import structlog
import httpx

from app.modules.research.sources.base import ResourceSource, RawResource
from app.config import settings

log = structlog.get_logger()

GITHUB_API = "https://api.github.com"


class GitHubSource(ResourceSource):
    """Discovers high-quality GitHub repositories for a topic."""

    @property
    def source_type(self) -> str:
        return "github"

    async def discover(self, topic: str, limit: int = 10) -> list[RawResource]:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if settings.has_github_token:
            headers["Authorization"] = f"Bearer {settings.GITHUB_TOKEN}"

        # Search for repos with good ML-related topics
        query = f"{topic} in:name,description,topic language:python stars:>50"

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(
                    f"{GITHUB_API}/search/repositories",
                    headers=headers,
                    params={"q": query, "sort": "stars", "order": "desc", "per_page": limit},
                )
                response.raise_for_status()
                data = response.json()
            except Exception as exc:
                log.error("GitHub search failed", topic=topic, error=str(exc))
                return []

        results = []
        for repo in data.get("items", []):
            results.append(RawResource(
                title=repo.get("full_name", ""),
                url=repo.get("html_url", ""),
                source_type="github",
                author=repo.get("owner", {}).get("login"),
                description=repo.get("description"),
                signals={
                    "stars": repo.get("stargazers_count", 0),
                    "forks": repo.get("forks_count", 0),
                    "updated_at": repo.get("updated_at"),
                    "topics": repo.get("topics", []),
                },
            ))

        return results
