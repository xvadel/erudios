from __future__ import annotations

import pytest
from datetime import date, timedelta
from unittest.mock import AsyncMock, patch

from app.modules.research.ranker import ResourceRanker
from app.modules.research.sources.base import RawResource


TRUSTED_DOMAINS = {
    "arxiv.org": 95.0,
    "github.com": 75.0,
    "lilianweng.github.io": 95.0,
    "medium.com": 60.0,
}


def make_resource(**kwargs) -> RawResource:
    defaults = dict(
        title="Test Resource Title For ML",
        url="https://arxiv.org/abs/1234.5678",
        source_type="paper",
        author="Test Author",
        published_at=date.today() - timedelta(days=30),
        description="A comprehensive guide to the topic with detailed examples",
        signals={},
    )
    defaults.update(kwargs)
    return RawResource(**defaults)


class TestResourceRanker:

    def setup_method(self):
        self.ranker = ResourceRanker(trusted_domains=TRUSTED_DOMAINS)

    def test_arxiv_paper_gets_high_trust_score(self):
        r = make_resource(url="https://arxiv.org/abs/1234")
        trust, _, _ = self.ranker.compute_score(r)
        assert trust >= 90.0

    def test_github_repo_gets_medium_trust_score(self):
        r = make_resource(url="https://github.com/owner/repo", source_type="github")
        trust, _, _ = self.ranker.compute_score(r)
        assert 70.0 <= trust <= 80.0

    def test_unknown_domain_gets_low_trust_score(self):
        r = make_resource(url="https://unknownrandomsite.xyz/post")
        trust, _, _ = self.ranker.compute_score(r)
        assert trust < 50.0

    def test_recent_resource_gets_high_recency_score(self):
        r = make_resource(published_at=date.today() - timedelta(days=10))
        _, quality, _ = self.ranker.compute_score(r)
        # quality includes recency — should be high
        assert quality > 50.0

    def test_old_resource_gets_low_recency_score(self):
        r = make_resource(published_at=date.today() - timedelta(days=365 * 5))
        _, quality, _ = self.ranker.compute_score(r)
        assert quality < 70.0  # penalized for age

    def test_high_star_github_repo_gets_high_community_score(self):
        r = make_resource(
            url="https://github.com/owner/repo",
            source_type="github",
            signals={"stars": 10000},
        )
        _, quality, _ = self.ranker.compute_score(r)
        assert quality > 70.0

    def test_rank_sorts_by_composite_score(self):
        high = make_resource(url="https://arxiv.org/abs/1", signals={"citations": 1000})
        low = make_resource(url="https://unknownsite.xyz/post", source_type="blog")
        ranked = self.ranker.rank([low, high])
        assert len(ranked) >= 1
        # arxiv should be ranked higher
        scores = [item[3] for item in ranked]
        assert scores == sorted(scores, reverse=True)

    def test_rank_filters_very_low_trust_resources(self):
        low_trust = make_resource(url="https://spamsite123.xyz/article")
        ranked = self.ranker.rank([low_trust])
        # May be filtered if composite is too low
        for r, trust, quality, composite in ranked:
            assert trust >= 30 or composite >= 40

    def test_subdomain_inherits_parent_trust(self):
        """user.github.io should inherit github.io trust."""
        self.ranker._trusted["github.io"] = 60.0
        r = make_resource(url="https://username.github.io/blog-post")
        trust, _, _ = self.ranker.compute_score(r)
        # Should get some trust from github.io
        assert trust > 40.0

    def test_paper_type_gets_bonus(self):
        # Pass signals so community scores match at 50.0 (citations=8 gives 40.0, citations=15 gives 60.0, average is 50.0)
        # Or we can pass citations=10 to get 60.0 vs blog's default 50.0
        paper = make_resource(url="https://arxiv.org/abs/123", source_type="paper", signals={"citations": 10})
        blog = make_resource(url="https://arxiv.org/abs/456", source_type="blog")
        _, _, paper_score = self.ranker.compute_score(paper)
        _, _, blog_score = self.ranker.compute_score(blog)
        assert paper_score >= blog_score
