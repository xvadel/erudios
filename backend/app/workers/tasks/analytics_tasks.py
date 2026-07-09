from __future__ import annotations

import uuid
import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from sqlalchemy.orm import selectinload

from app.db.session import AsyncSessionLocal
from app.models.quiz_attempt import QuizAttempt
from app.models.artifact import Quiz, ArtifactSection, ArtifactShell
from app.models.concept_mastery import ConceptMastery

log = structlog.get_logger()


async def update_concept_mastery_task(ctx, quiz_attempt_id: str) -> None:
    """
    Background arq task: aggregates a quiz attempt's answers into granular
    concept mastery stats (concept_mastery table).
    """
    attempt_uuid = uuid.UUID(quiz_attempt_id)
    log.info("Processing concept mastery for quiz attempt", attempt_id=quiz_attempt_id)

    async with AsyncSessionLocal() as db:
        try:
            # 1. Fetch QuizAttempt with Quiz, Section, and Shell
            attempt_result = await db.execute(
                select(QuizAttempt)
                .where(QuizAttempt.id == attempt_uuid)
                .options(
                    selectinload(QuizAttempt.quiz)
                    .selectinload(Quiz.section)
                    .selectinload(ArtifactSection.shell)
                )
            )
            attempt = attempt_result.scalar_one_or_none()
            if not attempt:
                log.warning("QuizAttempt not found in background task", attempt_id=quiz_attempt_id)
                return

            quiz = attempt.quiz
            questions = quiz.questions
            answers = attempt.answers_given
            user_id = attempt.user_id
            topic_id = quiz.section.shell.topic_id
            section_slug = quiz.section.section_slug

            # 2. Iterate answers and update concept aggregates
            for i, chosen_index in enumerate(answers):
                if i >= len(questions):
                    break
                
                q = questions[i]
                if not isinstance(q, dict):
                    continue

                concept = q.get("concept") or section_slug
                correct_index = q.get("correct_index")
                
                is_correct = (chosen_index == correct_index)

                # Fetch or create concept mastery row
                cm_result = await db.execute(
                    select(ConceptMastery).where(
                        ConceptMastery.user_id == user_id,
                        ConceptMastery.topic_id == topic_id,
                        ConceptMastery.section_slug == section_slug,
                        ConceptMastery.concept_label == concept,
                    )
                )
                cm = cm_result.scalar_one_or_none()
                if not cm:
                    cm = ConceptMastery(
                        user_id=user_id,
                        topic_id=topic_id,
                        section_slug=section_slug,
                        concept_label=concept,
                        correct_count=0,
                        incorrect_count=0,
                    )
                    db.add(cm)

                if is_correct:
                    cm.correct_count += 1
                else:
                    cm.incorrect_count += 1

            await db.commit()
            log.info("Successfully updated concept mastery from attempt", attempt_id=quiz_attempt_id)

        except Exception as exc:
            await db.rollback()
            log.error("Failed to update concept mastery in background", attempt_id=quiz_attempt_id, error=str(exc))
            raise


async def refresh_concept_performance(ctx) -> None:
    """arq task to refresh the materialized concept performance view."""
    log.info("Refreshing materialized view topic_concept_performance")
    async with AsyncSessionLocal() as db:
        try:
            # Refresh postgres materialized view
            await db.execute(text("REFRESH MATERIALIZED VIEW topic_concept_performance"))
            await db.commit()
            log.info("Successfully refreshed materialized view topic_concept_performance")
        except Exception as exc:
            await db.rollback()
            log.error("Failed to refresh materialized view", error=str(exc))
            raise
