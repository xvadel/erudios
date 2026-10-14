from __future__ import annotations

import math
import pytest
from app.modules.mastery.engine import MasteryEngine, MasterySignals


class TestMasteryEngine:
    def setup_method(self):
        self.engine = MasteryEngine(alpha=0.3)

    def test_ewma_first_quiz(self):
        # User starts with 0.0 mastery, gets 80 on first quiz
        signals = MasterySignals(
            recent_quiz_score=80.0,
            previous_mastery=0.0,
            quiz_attempt_count=0,
            days_since_reviewed=30,
        )
        score = self.engine.compute_mastery(signals)
        # Expected: 0.3 * 80.0 + 0.7 * 0.0 = 24.0
        assert score == 24.0

    def test_ewma_subsequent_improvement(self):
        # User has 24.0 mastery, gets 90 on second quiz
        signals = MasterySignals(
            recent_quiz_score=90.0,
            previous_mastery=24.0,
            quiz_attempt_count=1,
            days_since_reviewed=2,
        )
        score = self.engine.compute_mastery(signals)
        # Expected: 0.3 * 90.0 + 0.7 * 24.0 = 27.0 + 16.8 = 43.8
        assert score == 43.8

    def test_ewma_scores_remain_clamped(self):
        # High mastery remains capped at 100
        signals = MasterySignals(
            recent_quiz_score=100.0,
            previous_mastery=99.0,
            quiz_attempt_count=5,
            days_since_reviewed=1,
        )
        score = self.engine.compute_mastery(signals)
        assert score <= 100.0

    def test_stability_grows_with_attempts(self):
        s_0 = self.engine.compute_stability(0)
        s_1 = self.engine.compute_stability(1)
        s_5 = self.engine.compute_stability(5)

        # Base stability should be 7
        assert s_0 == 7.0
        # Grows as attempts increase
        assert s_1 == 10.5
        assert s_5 == 24.5

    def test_retention_factor_ebbinghaus(self):
        # S = 7 days. At t = 0 days, retention must be 1.0 (100%)
        r_0 = self.engine.compute_retention_factor(days_overdue=0, stability=7.0)
        assert r_0 == 1.0

        # At t = 7 days (exactly 1 stability interval), retention = e^-1 ~= 0.367, but clamped to floor of 0.5
        r_7 = self.engine.compute_retention_factor(days_overdue=7, stability=7.0)
        assert r_7 == 0.5  # Clamped to floor

        # S = 28 days. At t = 7 days, retention = e^(-7/28) = e^-0.25 ~= 0.778
        r_large = self.engine.compute_retention_factor(days_overdue=7, stability=28.0)
        assert math.isclose(r_large, 0.7788, abs_tol=1e-3)

    def test_next_review_interval(self):
        # 100% mastery with 2 reviews: S = 7 * (1 + 0.5 * 2) = 14
        # Interval = 14 * 1.0 = 14 days
        interval = self.engine.compute_next_review_interval_days(mastery_score=100.0, quiz_attempt_count=2)
        assert interval == 14.0

        # 50% mastery with 0 reviews: S = 7
        # Interval = 7 * 0.5 = 3.5 days
        interval_low = self.engine.compute_next_review_interval_days(mastery_score=50.0, quiz_attempt_count=0)
        assert interval_low == 3.5
