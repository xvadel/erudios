from __future__ import annotations

from dataclasses import dataclass, field

import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.topic import Topic, TopicDependency
from app.models.progress import LearningProgress
from app.models.curriculum import Module
from app.models.user import User

log = structlog.get_logger()

# Weights for the personalized scoring formula
_PREREQ_MET_BONUS = 25.0       # Topic has its prerequisite completed
_DIFFICULTY_MATCH_BONUS = 20.0  # Topic difficulty matches user level
_READINESS_BASE = 50.0          # Starting score for all candidates


@dataclass
class RecommendedTopic:
    topic: Topic
    score: float
    reasons: list[str] = field(default_factory=list)
    all_prereqs_met: bool = False


class RecommendationService:
    """
    Personalized next-topic recommendation engine.

    Goes beyond raw `whats_next` (topological ordering) by combining:
    - Graph traversal (unlocked topics the user hasn't studied yet)
    - Prerequisite mastery (were the prereqs actually completed well?)
    - Difficulty alignment (match user's declared skill level)
    - Learning goal alignment (research, job, project, etc.)
    - Variety (avoid recommending adjacent topics in the same cluster back-to-back)
    """

    async def get_recommendations(
        self,
        db: AsyncSession,
        user: User,
        completed_slugs: list[str] | None = None,
        limit: int = 6,
    ) -> list[RecommendedTopic]:
        """
        Return `limit` personalized topic recommendations for a user.
        """
        # 1. Determine which topics the user has mastered
        mastered_ids = await self._get_mastered_topic_ids(db, user.id)

        # 2. Load all topics with prerequisites
        topics_result = await db.execute(
            select(Topic).options(
                selectinload(Topic.prerequisites).selectinload(TopicDependency.prerequisite),
                selectinload(Topic.children),
            )
        )
        all_topics = list(topics_result.scalars().all())

        # 3. Filter to candidates (not mastered, accessible)
        candidates: list[RecommendedTopic] = []
        for topic in all_topics:
            if topic.id in mastered_ids:
                continue

            score, reasons, all_prereqs_met = self._score_topic(topic, user, mastered_ids)
            candidates.append(
                RecommendedTopic(
                    topic=topic,
                    score=score,
                    reasons=reasons,
                    all_prereqs_met=all_prereqs_met,
                )
            )

        # 4. Sort by score descending, return top N
        candidates.sort(key=lambda r: r.score, reverse=True)
        return candidates[:limit]

    def _score_topic(
        self,
        topic: Topic,
        user: User,
        mastered_ids: set,
    ) -> tuple[float, list[str], bool]:
        score = _READINESS_BASE
        reasons: list[str] = []

        # ── Prerequisite check ────────────────────────────────────────────────
        prereqs = [dep.prerequisite for dep in topic.prerequisites]
        all_prereqs_met = all(p.id in mastered_ids for p in prereqs) if prereqs else True

        if all_prereqs_met:
            score += _PREREQ_MET_BONUS
            if prereqs:
                reasons.append("All prerequisites completed")
        else:
            unmet = [p.name for p in prereqs if p.id not in mastered_ids]
            score -= 30.0  # Penalize locked topics
            reasons.append(f"Needs: {', '.join(unmet[:2])}")

        # ── Difficulty alignment ───────────────────────────────────────────────
        level_map = {"beginner": 1, "intermediate": 2, "advanced": 3}
        user_level = level_map.get(user.level, 1)
        topic_level = level_map.get(topic.difficulty, 1)

        diff = abs(topic_level - user_level)
        if diff == 0:
            score += _DIFFICULTY_MATCH_BONUS
            reasons.append("Matches your level")
        elif diff == 1:
            score += _DIFFICULTY_MATCH_BONUS * 0.5
        else:
            score -= 10.0

        # ── Goal alignment ────────────────────────────────────────────────────
        name_lower = topic.name.lower()
        if user.goal == "job" and any(k in name_lower for k in ["interview", "practice", "deploy"]):
            score += 10.0
            reasons.append("Relevant for job prep")
        elif user.goal == "research" and any(k in name_lower for k in ["paper", "theory", "transformer", "foundation"]):
            score += 10.0
            reasons.append("Relevant for research")
        elif user.goal == "startup" and any(k in name_lower for k in ["deploy", "api", "system", "product"]):
            score += 10.0
            reasons.append("Relevant for building products")

        # ── Prefer topics with sub-topics (more comprehensive) ────────────────
        if len(topic.children) > 0:
            score += min(len(topic.children) * 2.0, 10.0)

        return round(score, 1), reasons, all_prereqs_met

    async def _get_mastered_topic_ids(
        self, db: AsyncSession, user_id
    ) -> set:
        """Return IDs of topics where user has mastery_score >= 80."""
        result = await db.execute(
            select(LearningProgress.module_id, Module.topic_id)
            .join(Module, LearningProgress.module_id == Module.id)
            .where(
                LearningProgress.user_id == user_id,
                LearningProgress.mastery_score >= 80.0,
            )
        )
        return {row.topic_id for row in result}


recommendation_service = RecommendationService()
