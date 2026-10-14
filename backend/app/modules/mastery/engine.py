from __future__ import annotations

import math
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel


class MasterySignals(BaseModel):
    recent_quiz_score: float      # score from the current attempt (0-100)
    previous_mastery: float       # previous mastery score (0-100)
    quiz_attempt_count: int       # raw attempt count for this topic/module
    days_since_reviewed: int      # days since last review


class MasteryEngine:
    """
    Pure mathematical model for knowledge mastery and spaced repetition retention.
    
    Principles:
    1. EWMA (Exponentially Weighted Moving Average) for scoring (alpha = 0.3)
    2. Ebbinghaus forgetting curve for retention decay status
    3. SM-2 interval logic for spaced repetition scheduling (stability increases with reviews)
    """

    def __init__(self, alpha: float = 0.3) -> None:
        self.alpha = alpha

    def compute_mastery(self, signals: MasterySignals) -> float:
        """
        Compute new mastery score using EWMA.
        EWMA adjusts score dynamically without penalizing early mistakes forever.
        """
        new_mastery = (self.alpha * signals.recent_quiz_score) + ((1.0 - self.alpha) * signals.previous_mastery)
        return round(min(100.0, max(0.0, new_mastery)), 1)

    def compute_retention_factor(self, days_overdue: float, stability: float) -> float:
        """
        Ebbinghaus forgetting curve factor: R = e^(-t/S)
        Where S is the stability (half-life of knowledge).
        Returns a factor in range [0.5, 1.0].
        """
        if stability <= 0:
            stability = 1.0
        retention = math.exp(-days_overdue / stability)
        return max(0.5, min(1.0, retention))

    def compute_stability(self, quiz_attempt_count: int) -> float:
        """
        Stability (days until retention drops significantly) grows with the number of reviews.
        S = 7 * (1 + 0.5 * attempts)
        """
        return 7.0 * (1.0 + 0.5 * max(0, quiz_attempt_count))

    def compute_next_review_interval_days(self, mastery_score: float, quiz_attempt_count: int) -> float:
        """
        Calculates review interval in days.
        Higher mastery and count = longer interval.
        """
        stability = self.compute_stability(quiz_attempt_count)
        mastery_factor = max(0.1, min(1.0, mastery_score / 100.0))
        return max(1.0, stability * mastery_factor)
