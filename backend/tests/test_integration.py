from __future__ import annotations

import pytest
import pytest_asyncio
import uuid
from datetime import datetime, timezone
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models import (
    User, Topic, Curriculum, Module, Quiz, ArtifactSection, ArtifactShell,
    LearningProgress, QuizAttempt, ConceptMastery, Resource, ResourceFeedback
)
from app.core.security import create_access_token
from app.workers.tasks.analytics_tasks import update_concept_mastery_task
from app.modules.research.feedback import resource_feedback_service
from app.services.cache import cache_service


@pytest_asyncio.fixture(scope="function", autouse=True)
async def setup_cache():
    await cache_service.connect()
    yield
    await cache_service.disconnect()


async def get_test_headers(client: AsyncClient, db: AsyncSession) -> dict[str, str]:
    """Helper to seed a test user and obtain auth headers/mock token."""
    # Check if test user exists
    res = await db.execute(select(User).where(User.username == "test_mastery_user"))
    user = res.scalar_one_or_none()
    if not user:
        user = User(
            username="test_mastery_user",
            name="Test Mastery User",
            password_hash="fakehash",
            level="beginner",
            learning_style="practical",
            goal="general",
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    token = create_access_token(str(user.id))
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_quiz_attempt_and_mastery_flow(client: AsyncClient, db: AsyncSession):
    # 1. Setup Auth
    headers = await get_test_headers(client, db)
    user_res = await db.execute(select(User).where(User.username == "test_mastery_user"))
    user = user_res.scalar_one()

    # 2. Seed Topic, Curriculum, Module, Shell, Section, and Quiz
    topic = Topic(name="Neural Networks", slug="neural-networks", difficulty="beginner")
    db.add(topic)
    await db.commit()
    await db.refresh(topic)

    curr = Curriculum(
        user_id=user.id,
        root_topic_id=topic.id,
        level="beginner",
        learning_style="practical",
        goal="general",
        cache_key="test-curriculum-key",
    )
    db.add(curr)
    await db.commit()
    await db.refresh(curr)

    module = Module(
        curriculum_id=curr.id,
        topic_id=topic.id,
        title="Intro to NN",
        difficulty="beginner",
        order_index=0,
    )
    db.add(module)
    await db.commit()
    await db.refresh(module)

    shell = ArtifactShell(
        topic_id=topic.id,
        overview="NN Overview",
        section_titles=[],
        cache_key="neural-networks-shell-key",
    )
    db.add(shell)
    await db.commit()
    await db.refresh(shell)

    section = ArtifactSection(
        shell_id=shell.id,
        section_slug="intro-to-nn",
        section_title="Intro",
        base_content="Intro text",
        style_overlays={},
        cache_key="neural-networks-intro-section-key",
        order_index=0,
    )
    db.add(section)
    await db.commit()
    await db.refresh(section)

    quiz = Quiz(
        section_id=section.id,
        version=1,
        cache_key="neural-networks-intro-quiz-key",
        questions=[
            {
                "question": "What is an activation function?",
                "options": ["A", "B", "C"],
                "correct_index": 0,
                "concept": "activation-functions",
            },
            {
                "question": "What is gradient descent?",
                "options": ["X", "Y", "Z"],
                "correct_index": 1,
                "concept": "optimization",
            },
        ],
    )
    db.add(quiz)
    await db.commit()
    await db.refresh(quiz)

    # 3. Submit quiz result via POST
    payload = {
        "quiz_id": str(quiz.id),
        "score": 50.0,
        "answers_given": [0, 2],  # Question 0 correct (0==0), Question 1 wrong (2!=1)
        "time_spent_minutes": 5,
        "time_taken_seconds": 300,
    }
    
    response = await client.post(
        f"/api/v1/progress/modules/{module.id}/quiz-result",
        json=payload,
        headers=headers,
    )
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["quizzes_taken"] == 1
    assert res_data["avg_quiz_score"] == 50.0

    # 4. Verify QuizAttempt was persisted in DB
    attempts_result = await db.execute(select(QuizAttempt).where(QuizAttempt.user_id == user.id))
    attempts = attempts_result.scalars().all()
    assert len(attempts) == 1
    attempt = attempts[0]
    assert attempt.score == 50.0
    assert attempt.answers_given == [0, 2]

    # Commit test transaction to allow the separate session in the background task to read it
    await db.commit()

    # 5. Run the background concept mastery aggregation task synchronously
    await update_concept_mastery_task(ctx=None, quiz_attempt_id=str(attempt.id))

    # 6. Verify ConceptMastery records were created/updated
    cm_activation = (
        await db.execute(
            select(ConceptMastery).where(
                ConceptMastery.user_id == user.id,
                ConceptMastery.concept_label == "activation-functions",
            )
        )
    ).scalar_one()
    assert cm_activation.correct_count == 1
    assert cm_activation.incorrect_count == 0

    cm_optimization = (
        await db.execute(
            select(ConceptMastery).where(
                ConceptMastery.user_id == user.id,
                ConceptMastery.concept_label == "optimization",
            )
        )
    ).scalar_one()
    assert cm_optimization.correct_count == 0
    assert cm_optimization.incorrect_count == 1


@pytest.mark.asyncio
async def test_resource_feedback_and_bookmarks_flow(client: AsyncClient, db: AsyncSession):
    # 1. Setup Auth
    headers = await get_test_headers(client, db)
    user_res = await db.execute(select(User).where(User.username == "test_mastery_user"))
    user = user_res.scalar_one()

    # 2. Seed Topic and Resource
    topic = Topic(name="Deep Learning", slug="deep-learning", difficulty="intermediate")
    db.add(topic)
    await db.commit()
    await db.refresh(topic)

    resource = Resource(
        topic_id=topic.id,
        title="Deep Learning Book",
        url="https://example-deeplearningbook.org",
        source_type="blog",
        trust_score=60.0,
        quality_score=60.0,
        composite_score=60.0,
    )
    db.add(resource)
    await db.commit()
    await db.refresh(resource)

    # 3. Rate the resource (helpful rating=1) and bookmark it
    payload = {
        "rating": 1,
        "bookmarked": True,
        "completed": False,
        "time_spent_seconds": 120,
    }
    response = await client.post(
        f"/api/v1/resources/{resource.id}/feedback",
        json=payload,
        headers=headers,
    )
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["bookmarked"] is True
    assert res_data["rating"] == 1

    # Verify database state
    db_res = await db.get(Resource, resource.id)
    # The composite score should be updated since positive rating was submitted
    assert db_res.feedback_count == 1
    assert db_res.feedback_score == 52.5

    # 4. Fetch Bookmarks
    bookmarks_response = await client.get("/api/v1/resources/bookmarks", headers=headers)
    assert bookmarks_response.status_code == 200
    bookmarks = bookmarks_response.json()
    assert len(bookmarks) == 1
    assert bookmarks[0]["id"] == str(resource.id)
    assert bookmarks[0]["user_feedback"]["bookmarked"] is True
