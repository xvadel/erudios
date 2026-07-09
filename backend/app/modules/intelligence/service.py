from __future__ import annotations

import uuid
import structlog
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.progress import LearningProgress
from app.models.curriculum import Module
from app.models.topic import Topic, TopicDependency
from app.models.user import User
from app.services.cache import cache_service
from app.modules.recommendation.service import recommendation_service
from app.modules.mastery.analytics import quiz_analytics_service, ConceptPerformance

log = structlog.get_logger()


class ReviewItem(BaseModel):
    module_id: uuid.UUID
    topic_slug: str
    topic_name: str
    mastery_score: float
    next_review: datetime


class BlockingPrereq(BaseModel):
    topic_name: str
    prereq_name: str
    prereq_slug: str
    mastery_score: float


class RecommendationOut(BaseModel):
    """Pydantic-safe DTO for a recommended topic (no SQLAlchemy objects)."""
    topic_slug: str
    topic_name: str
    difficulty: str
    estimated_hours: float
    score: float
    reasons: list[str]
    all_prereqs_met: bool


class DailyPlan(BaseModel):
    review_items: list[ReviewItem]
    new_topics: list[RecommendationOut]
    weak_concepts: list[ConceptPerformance]
    blocking_prereqs: list[BlockingPrereq]
    estimated_minutes: int
    brief: str


class LearningIntelligenceService:
    """
    Intelligent learning engine compiling personalized daily learning plans,
    spaced repetition schedules, and contextual coaching briefs.
    """

    async def get_daily_plan(self, db: AsyncSession, user: User) -> DailyPlan:
        """
        Synthesizes today's personalized plan by checking:
        1. Overdue spaced repetition modules
        2. Personal topic recommendations
        3. Concept weaknesses/gaps
        4. Prerequisite blockages
        """
        # 1. Fetch items due for review (SM-2 logic)
        review_items = await self.get_review_queue(db, user.id, limit=3)

        # 2. Fetch new topic recommendations — convert dataclass to Pydantic DTO
        rec_list = await recommendation_service.get_recommendations(db, user, limit=2)
        new_topics = [
            RecommendationOut(
                topic_slug=r.topic.slug,
                topic_name=r.topic.name,
                difficulty=r.topic.difficulty,
                estimated_hours=r.topic.estimated_hours,
                score=r.score,
                reasons=r.reasons,
                all_prereqs_met=r.all_prereqs_met,
            )
            for r in rec_list
        ]

        # 3. Fetch weak concepts
        # Aggregate across all topics the user is active in
        weak_concepts = await self._get_active_weak_concepts(db, user.id)

        # 4. Fetch blocking prerequisites
        blocking_prereqs = await self.get_blocking_prerequisites(db, user.id)

        # 5. Estimate study time (15 mins per review + 30 mins per new topic + 10 mins per weak concept)
        est_min = (len(review_items) * 15) + (len(new_topics) * 30) + (len(weak_concepts) * 10)

        # 6. Resolve Daily Brief narrative (cached for 24h)
        brief = await self.get_daily_brief(db, user, len(review_items), len(new_topics), weak_concepts)

        return DailyPlan(
            review_items=review_items,
            new_topics=new_topics,
            weak_concepts=weak_concepts,
            blocking_prereqs=blocking_prereqs,
            estimated_minutes=est_min,
            brief=brief,
        )

    async def get_review_queue(
        self, db: AsyncSession, user_id: uuid.UUID, limit: int = 5
    ) -> list[ReviewItem]:
        """Fetch all learning progress rows where review date is due/overdue."""
        now = datetime.now(timezone.utc)
        result = await db.execute(
            select(LearningProgress)
            .where(
                LearningProgress.user_id == user_id,
                LearningProgress.next_review <= now,
            )
            .options(selectinload(LearningProgress.module).selectinload(Module.topic))
            .order_by(LearningProgress.mastery_score.asc())
            .limit(limit)
        )
        progress_list = result.scalars().all()
        return [
            ReviewItem(
                module_id=p.module_id,
                topic_slug=p.module.topic.slug,
                topic_name=p.module.topic.name,
                mastery_score=p.mastery_score,
                next_review=p.next_review,
            )
            for p in progress_list
            if p.module and p.module.topic
        ]

    async def get_blocking_prerequisites(
        self, db: AsyncSession, user_id: uuid.UUID
    ) -> list[BlockingPrereq]:
        """
        Identify active topics where the user has started learning but is blocked by
        a prerequisite topic with low mastery (< 60.0).
        """
        # Load user active progress topics
        result = await db.execute(
            select(LearningProgress)
            .where(LearningProgress.user_id == user_id)
            .options(selectinload(LearningProgress.module).selectinload(Module.topic))
        )
        active_progress = result.scalars().all()
        active_topic_ids = {p.module.topic_id for p in active_progress if p.module}
        mastery_map = {p.module.topic_id: p.mastery_score for p in active_progress if p.module}

        blocking = []
        for t_id in active_topic_ids:
            # Check prerequisites of this active topic
            prereq_result = await db.execute(
                select(TopicDependency)
                .where(TopicDependency.dependent_id == t_id)
                .options(selectinload(TopicDependency.prerequisite), selectinload(TopicDependency.dependent))
            )
            deps = prereq_result.scalars().all()
            for dep in deps:
                prereq_mastery = mastery_map.get(dep.prerequisite_id, 0.0)
                if prereq_mastery < 60.0:
                    blocking.append(
                        BlockingPrereq(
                            topic_name=dep.dependent.name,
                            prereq_name=dep.prerequisite.name,
                            prereq_slug=dep.prerequisite.slug,
                            mastery_score=prereq_mastery,
                        )
                    )
        return blocking[:5]

    async def get_daily_brief(
        self,
        db: AsyncSession,
        user: User,
        review_count: int,
        new_count: int,
        weak_concepts: list[ConceptPerformance],
    ) -> str:
        """
        Resolves the motivational narrative brief, using deterministic templating
        to minimize LLM tokens, with cached Redis lookups.
        """
        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        cache_key = f"daily_brief:{user.id}:{today_str}"
        
        cached = await cache_service.get(cache_key)
        if cached:
            return str(cached)

        # ── Deterministic template generation ───────────────────────────────
        if review_count > 0:
            msg = f"Welcome back, {user.name}! Today, we should focus on reviewing {review_count} topics that are due. "
            if weak_concepts:
                msg += f"In particular, you've struggled with '{weak_concepts[0].concept_label}' recently. "
            msg += "Let's reinforce this foundation before tackling new concepts."
        elif new_count > 0:
            msg = f"Excellent job, {user.name}! You are fully caught up on your reviews. Today is a great day to explore new topics! "
            msg += f"We suggest diving into your top recommendation to keep the momentum going."
        else:
            msg = f"Hey {user.name}! All your reviews are fresh and up to date. Keep learning at your own pace!"

        # Cache for 24 hours
        await cache_service.set(cache_key, msg, ttl=86400)
        return msg

    async def _get_active_weak_concepts(
        self, db: AsyncSession, user_id: uuid.UUID
    ) -> list[ConceptPerformance]:
        """Fetch weak concepts across all currently studied topics."""
        # Get active modules from progress
        res = await db.execute(
            select(LearningProgress.module_id)
            .where(LearningProgress.user_id == user_id)
        )
        mod_ids = [row[0] for row in res.fetchall()]
        if not mod_ids:
            return []

        # Find the corresponding topic IDs
        topics_res = await db.execute(
            select(Module.topic_id).where(Module.id.in_(mod_ids))
        )
        topic_ids = [row[0] for row in topics_res.fetchall()]
        
        weak_list = []
        for t_id in set(topic_ids):
            w = await quiz_analytics_service.get_weak_concepts(db, user_id, t_id, threshold=60.0)
            weak_list.extend(w)
            if len(weak_list) >= 3:
                break
        return weak_list[:3]


learning_intelligence_service = LearningIntelligenceService()
