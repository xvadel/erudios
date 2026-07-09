from __future__ import annotations

import uuid
import structlog
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.progress import LearningProgress
from app.modules.mastery.engine import MasteryEngine, MasterySignals

log = structlog.get_logger()


class MasteryService:
    """
    Service layer coordinating mastery score updates, status checks,
    and review intervals.
    """

    def __init__(self, engine: MasteryEngine | None = None) -> None:
        self.engine = engine or MasteryEngine()

    async def get_or_create_progress(
        self, db: AsyncSession, user_id: uuid.UUID, module_id: uuid.UUID
    ) -> LearningProgress:
        """Fetch or initialize learning progress for a user module."""
        result = await db.execute(
            select(LearningProgress).where(
                LearningProgress.user_id == user_id,
                LearningProgress.module_id == module_id,
            )
        )
        progress = result.scalar_one_or_none()
        if not progress:
            progress = LearningProgress(user_id=user_id, module_id=module_id)
            db.add(progress)
            await db.flush()
        return progress

    async def record_quiz_result(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        module_id: uuid.UUID,
        score: float,
        time_spent_minutes: int = 0,
    ) -> LearningProgress:
        """
        Processes a new quiz result. Computes EWMA mastery and schedules next review.
        """
        progress = await self.get_or_create_progress(db, user_id, module_id)

        # Build signals for the math engine
        signals = MasterySignals(
            recent_quiz_score=score,
            previous_mastery=progress.mastery_score,
            quiz_attempt_count=progress.quiz_attempt_count,
            days_since_reviewed=self._days_since(progress.last_reviewed),
        )

        # Update stats
        progress.quiz_attempt_count += 1
        progress.quizzes_taken += 1
        
        # Keep best score
        progress.best_quiz_score = max(progress.best_quiz_score, score)

        # Calculate new average quiz score
        total_prev_score = progress.avg_quiz_score * (progress.quizzes_taken - 1)
        progress.avg_quiz_score = round((total_prev_score + score) / progress.quizzes_taken, 1)

        # Calculate new mastery using pure EWMA
        progress.mastery_score = self.engine.compute_mastery(signals)

        # Accumulate time
        progress.time_spent_minutes += time_spent_minutes
        
        # Mark reviewed now
        now_utc = datetime.now(timezone.utc)
        progress.last_reviewed = now_utc

        # Compute next review date
        interval_days = self.engine.compute_next_review_interval_days(
            progress.mastery_score, progress.quiz_attempt_count
        )
        progress.next_review = now_utc + timedelta(days=interval_days)

        log.info(
            "Mastery updated via EWMA",
            user_id=user_id,
            module_id=module_id,
            score=score,
            mastery=progress.mastery_score,
            next_review=progress.next_review.isoformat(),
        )

        await db.flush()
        return progress

    def get_review_status(self, progress: LearningProgress) -> str:
        """
        Returns the review status for a progress row: fresh | due | overdue.
        """
        if not progress.next_review:
            return "fresh"
        
        # Ensure timezone-aware comparison
        next_rev = progress.next_review
        if next_rev.tzinfo is None:
            next_rev = next_rev.replace(tzinfo=timezone.utc)

        now = datetime.now(timezone.utc)
        if now < next_rev:
            return "fresh"
        elif now < next_rev + timedelta(days=7):
            return "due"
        else:
            return "overdue"

    def _days_since(self, last_date: datetime | None) -> int:
        if not last_date:
            return 30  # Default value if never reviewed
        
        if last_date.tzinfo is None:
            last_date = last_date.replace(tzinfo=timezone.utc)
            
        delta = datetime.now(timezone.utc) - last_date
        return max(0, delta.days)


mastery_service = MasteryService()
