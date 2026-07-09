from __future__ import annotations

import uuid
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, text
from pydantic import BaseModel


class ConceptPerformance(BaseModel):
    concept_label: str
    section_slug: str
    total_correct: int
    total_incorrect: int
    accuracy_pct: float


class RepeatedMistake(BaseModel):
    concept_label: str
    section_slug: str
    incorrect_count: int


class DailyScoreTrend(BaseModel):
    date: str
    avg_score: float


class LearningSummary(BaseModel):
    total_mastery_points: float
    streak_days: int
    total_quizzes_taken: int
    learning_velocity: float  # average quiz score increase rate or overall mastery score


class QuizAnalyticsService:
    """
    Analytics engine extracting performance trends, weak/strong concepts,
    and repeated mistake patterns from the database/materialized view.
    """

    async def get_weak_concepts(
        self, db: AsyncSession, user_id: uuid.UUID, topic_id: uuid.UUID, threshold: float = 60.0
    ) -> list[ConceptPerformance]:
        """Fetch concepts for a user and topic where accuracy is below the threshold."""
        query = text(
            """
            SELECT concept_label, section_slug, total_correct, total_incorrect, accuracy_pct
            FROM topic_concept_performance
            WHERE user_id = :user_id AND topic_id = :topic_id AND accuracy_pct < :threshold
            ORDER BY accuracy_pct ASC
            """
        )
        result = await db.execute(query, {"user_id": user_id, "topic_id": topic_id, "threshold": threshold})
        return [
            ConceptPerformance(
                concept_label=row[0],
                section_slug=row[1],
                total_correct=row[2],
                total_incorrect=row[3],
                accuracy_pct=float(row[4]),
            )
            for row in result.fetchall()
        ]

    async def get_strong_concepts(
        self, db: AsyncSession, user_id: uuid.UUID, topic_id: uuid.UUID, threshold: float = 85.0
    ) -> list[ConceptPerformance]:
        """Fetch concepts for a user and topic where accuracy meets or exceeds the threshold."""
        query = text(
            """
            SELECT concept_label, section_slug, total_correct, total_incorrect, accuracy_pct
            FROM topic_concept_performance
            WHERE user_id = :user_id AND topic_id = :topic_id AND accuracy_pct >= :threshold
            ORDER BY accuracy_pct DESC
            """
        )
        result = await db.execute(query, {"user_id": user_id, "topic_id": topic_id, "threshold": threshold})
        return [
            ConceptPerformance(
                concept_label=row[0],
                section_slug=row[1],
                total_correct=row[2],
                total_incorrect=row[3],
                accuracy_pct=float(row[4]),
            )
            for row in result.fetchall()
        ]

    async def get_repeated_mistakes(
        self, db: AsyncSession, user_id: uuid.UUID, limit: int = 10
    ) -> list[RepeatedMistake]:
        """Identify concepts where the user made multiple incorrect answers (incorrect > 1)."""
        query = text(
            """
            SELECT concept_label, section_slug, SUM(incorrect_count) as total_incorrect
            FROM concept_mastery
            WHERE user_id = :user_id
            GROUP BY concept_label, section_slug
            HAVING SUM(incorrect_count) > 1
            ORDER BY total_incorrect DESC
            LIMIT :limit
            """
        )
        result = await db.execute(query, {"user_id": user_id, "limit": limit})
        return [
            RepeatedMistake(
                concept_label=row[0],
                section_slug=row[1],
                incorrect_count=int(row[2]),
            )
            for row in result.fetchall()
        ]

    async def get_topic_performance_trend(
        self, db: AsyncSession, user_id: uuid.UUID, topic_id: uuid.UUID, days: int = 30
    ) -> list[DailyScoreTrend]:
        """Returns daily average quiz score trend for a specific topic over the last N days."""
        query = text(
            """
            SELECT TO_CHAR(created_at, 'YYYY-MM-DD') as day, ROUND(AVG(score)::numeric, 1) as avg_score
            FROM quiz_attempts
            WHERE user_id = :user_id AND created_at >= NOW() - INTERVAL '1 day' * :days
            GROUP BY TO_CHAR(created_at, 'YYYY-MM-DD')
            ORDER BY day ASC
            """
        )
        result = await db.execute(query, {"user_id": user_id, "days": days})
        return [
            DailyScoreTrend(
                date=row[0],
                avg_score=float(row[1]),
            )
            for row in result.fetchall()
        ]

    async def get_learning_summary(
        self, db: AsyncSession, user_id: uuid.UUID
    ) -> LearningSummary:
        """Computes aggregate velocity, streak, and mastery levels for the user profile."""
        # 1. Total mastery score sum
        mastery_query = text(
            "SELECT SUM(mastery_score) FROM learning_progress WHERE user_id = :user_id"
        )
        mastery_result = await db.execute(mastery_query, {"user_id": user_id})
        mastery_sum = mastery_result.scalar() or 0.0

        # 2. Total quizzes taken sum
        quizzes_query = text(
            "SELECT SUM(quizzes_taken) FROM learning_progress WHERE user_id = :user_id"
        )
        quizzes_result = await db.execute(quizzes_query, {"user_id": user_id})
        quizzes_sum = quizzes_result.scalar() or 0

        # 3. Streak days
        streak_query = text(
            "SELECT MAX(streak_days) FROM learning_progress WHERE user_id = :user_id"
        )
        streak_result = await db.execute(streak_query, {"user_id": user_id})
        streak_days = streak_result.scalar() or 0

        # Calculate learning velocity (average mastery gain per active module)
        velocity_query = text(
            """
            SELECT AVG(mastery_score) FROM learning_progress 
            WHERE user_id = :user_id AND quizzes_taken > 0
            """
        )
        velocity_result = await db.execute(velocity_query, {"user_id": user_id})
        velocity = velocity_result.scalar() or 0.0

        return LearningSummary(
            total_mastery_points=float(mastery_sum),
            streak_days=int(streak_days),
            total_quizzes_taken=int(quizzes_sum),
            learning_velocity=round(float(velocity), 1),
        )


quiz_analytics_service = QuizAnalyticsService()
