from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.modules.artifacts.service import artifact_service
from app.core.exceptions import NotFoundError
from app.schemas.artifact import SectionInfo, ShellOut, SectionOut, QuizQuestion, QuizOut

router = APIRouter()


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/{topic_slug}/shell", response_model=ShellOut)
async def get_artifact_shell(
    topic_slug: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get (or lazily generate) the artifact shell for a topic.
    Returns an overview and ordered list of section titles.
    First call triggers generation (~1-2 s). Subsequent calls are instant.
    No auth required — content is shared globally.
    """
    shell = await artifact_service.get_or_generate_shell(db, topic_slug)
    sections = [
        SectionInfo(slug=s["slug"], title=s["title"])
        for s in shell.get("sections", [])
    ]
    return ShellOut(
        topic_slug=topic_slug,
        overview=shell.get("overview", ""),
        sections=sections,
    )


@router.get("/{topic_slug}/sections/{section_slug}", response_model=SectionOut)
async def get_section_content(
    topic_slug: str,
    section_slug: str,
    style: str | None = Query(
        None,
        description="Learning style for personalized overlay: visual|practical|research|interview|project"
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    Get (or lazily generate) content for a specific section.
    Pass ?style=visual to get a personalized style overlay merged with base content.
    If style overlay generation fails (budget exhausted), returns base content
    with degraded=true so the frontend can display an appropriate notice.
    No auth required — base content and overlays are shared globally.
    """
    # Resolve section title from shell (needed for generation prompts)
    shell = await artifact_service.get_or_generate_shell(db, topic_slug)
    section_title = next(
        (s["title"] for s in shell.get("sections", []) if s["slug"] == section_slug),
        section_slug.replace("-", " ").title(),  # Fallback title from slug
    )

    result = await artifact_service.get_or_generate_section(
        db=db,
        topic_slug=topic_slug,
        section_slug=section_slug,
        section_title=section_title,
        learning_style=style,
    )

    return SectionOut(
        topic_slug=topic_slug,
        section_slug=section_slug,
        content=result["content"],
        has_overlay=result["has_overlay"],
        degraded=result["degraded"],
    )


@router.get("/{topic_slug}/sections/{section_slug}/quiz", response_model=QuizOut)
async def get_section_quiz(
    topic_slug: str,
    section_slug: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get (or lazily generate) quiz questions for a section.
    Returns 5 multiple-choice questions with explanations.
    No auth required — quizzes are shared globally.
    """
    shell = await artifact_service.get_or_generate_shell(db, topic_slug)
    section_title = next(
        (s["title"] for s in shell.get("sections", []) if s["slug"] == section_slug),
        section_slug.replace("-", " ").title(),
    )

    questions_raw = await artifact_service.get_or_generate_quiz(
        db=db,
        topic_slug=topic_slug,
        section_slug=section_slug,
        section_title=section_title,
    )

    questions = [
        QuizQuestion(
            question=q.get("question", ""),
            options=q.get("options", []),
            correct_index=q.get("correct_index", 0),
            explanation=q.get("explanation", ""),
        )
        for q in questions_raw
        if q.get("question") and q.get("options")
    ]

    return QuizOut(
        topic_slug=topic_slug,
        section_slug=section_slug,
        questions=questions,
    )
