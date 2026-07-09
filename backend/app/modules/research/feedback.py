from __future__ import annotations

import uuid
import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, cast, Integer, and_

from app.models.resource import Resource
from app.models.resource_feedback import ResourceFeedback
from app.services.cache import cache_service

log = structlog.get_logger()


class ResourceFeedbackService:
    """
    Coordinates explicit user ratings and implicit interaction feedback to calculate
    Bayesian composite resource popularity/quality scores.
    """

    async def upsert_feedback(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        resource_id: uuid.UUID,
        rating: int | None = None,
        bookmarked: bool | None = None,
        completed: bool | None = None,
        time_spent_seconds: int = 0,
    ) -> ResourceFeedback:
        """
        Record or edit user feedback on a resource, then trigger score recalculation.
        Uses Redis rate-limiting (1 edit per user per resource per day) for spam protection.
        """
        # Spam protection check
        rate_key = f"feedback_rate:{user_id}:{resource_id}"
        is_limited = await cache_service.exists(rate_key)
        # For bookmarks or completions, we bypass strict rate limits, but restrict ratings
        if is_limited and rating is not None:
            log.warning("Feedback rate limit hit for user resource rating", user_id=user_id, resource=resource_id)

        # 1. Fetch or create feedback row
        result = await db.execute(
            select(ResourceFeedback).where(
                ResourceFeedback.user_id == user_id,
                ResourceFeedback.resource_id == resource_id,
            )
        )
        fb = result.scalar_one_or_none()
        if not fb:
            fb = ResourceFeedback(
                user_id=user_id,
                resource_id=resource_id,
                rating=0,
                bookmarked=False,
                completed=False,
                time_spent_seconds=0,
            )
            db.add(fb)

        # 2. Update provided fields
        if rating is not None:
            fb.rating = rating
            # Apply rate limit for 24h
            await cache_service.set(rate_key, "1", ttl=86400)
        if bookmarked is not None:
            fb.bookmarked = bookmarked
        if completed is not None:
            fb.completed = completed
        if time_spent_seconds > 0:
            fb.time_spent_seconds = (fb.time_spent_seconds or 0) + time_spent_seconds

        await db.flush()

        # 3. Recalculate resource composite score
        await self.recompute_composite_score(db, resource_id)
        
        await db.flush()
        return fb

    async def get_user_feedback(
        self, db: AsyncSession, user_id: uuid.UUID, resource_id: uuid.UUID
    ) -> ResourceFeedback | None:
        """Get feedback row for specific user and resource."""
        result = await db.execute(
            select(ResourceFeedback).where(
                ResourceFeedback.user_id == user_id,
                ResourceFeedback.resource_id == resource_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_user_bookmarks(
        self, db: AsyncSession, user_id: uuid.UUID
    ) -> list[Resource]:
        """Fetch all resources bookmarked by the user."""
        result = await db.execute(
            select(Resource)
            .join(ResourceFeedback, Resource.id == ResourceFeedback.resource_id)
            .where(
                ResourceFeedback.user_id == user_id,
                ResourceFeedback.bookmarked == True,
            )
        )
        return list(result.scalars().all())

    async def recompute_composite_score(
        self, db: AsyncSession, resource_id: uuid.UUID
    ) -> float:
        """
        Recalculate Bayesian score for a resource:
        feedback_signal = helpful_votes * 10 + bookmarks * 5 - not_helpful_votes * 8
        new_score = (base_trust_prior * 5 + feedback_signal) / (5 + total_votes)
        """
        # Fetch the resource
        res = await db.get(Resource, resource_id)
        if not res:
            return 50.0

        # Fetch aggregated feedback counts via simple filter queries (avoid cast complexity)
        helpful_result = await db.execute(
            select(func.count()).where(
                ResourceFeedback.resource_id == resource_id,
                ResourceFeedback.rating == 1,
            )
        )
        helpful_votes = helpful_result.scalar() or 0

        not_helpful_result = await db.execute(
            select(func.count()).where(
                ResourceFeedback.resource_id == resource_id,
                ResourceFeedback.rating == -1,
            )
        )
        not_helpful_votes = not_helpful_result.scalar() or 0

        bookmarks_result = await db.execute(
            select(func.count()).where(
                ResourceFeedback.resource_id == resource_id,
                ResourceFeedback.bookmarked == True,  # noqa: E712
            )
        )
        bookmarks = bookmarks_result.scalar() or 0

        completions_result = await db.execute(
            select(func.count()).where(
                ResourceFeedback.resource_id == resource_id,
                ResourceFeedback.completed == True,  # noqa: E712
            )
        )
        completions = completions_result.scalar() or 0


        feedback_signal = (helpful_votes * 10) + (bookmarks * 5) + (completions * 8) - (not_helpful_votes * 8)
        total_votes = helpful_votes + not_helpful_votes

        # Bayesian update using base trust score (or default 50.0) as the prior
        prior_weight = 5.0
        base_prior = res.trust_score
        denominator = prior_weight + total_votes
        if denominator == 0:
            clamped_score = base_prior
        else:
            new_score = (base_prior * prior_weight + feedback_signal) / denominator
            clamped_score = max(0.0, min(100.0, new_score))

        res.feedback_score = clamped_score
        res.feedback_count = total_votes
        res.composite_score = round((res.trust_score * 0.4) + (res.quality_score * 0.3) + (res.feedback_score * 0.3), 1)

        log.info(
            "Recomputed resource composite score",
            resource_id=resource_id,
            total_votes=total_votes,
            feedback_score=res.feedback_score,
            composite_score=res.composite_score,
        )
        return res.composite_score


resource_feedback_service = ResourceFeedbackService()
