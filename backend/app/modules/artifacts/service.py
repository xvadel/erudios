from __future__ import annotations

import json

import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.artifact import ArtifactShell, ArtifactSection, Quiz
from app.models.topic import Topic
from app.services.cache import cache_service
from app.providers.llms.router import provider_router
from app.providers.llms.budget import TaskType
from app.modules.topic_graph.service import topic_graph_service
from app.core.exceptions import NotFoundError
from app.config import settings

log = structlog.get_logger()


# ── Style descriptions for prompts ─────────────────────────────────────────────

STYLE_PROMPTS: dict[str, str] = {
    "visual": (
        "Add a 'Visual Mental Model' subsection with a text-based diagram or analogy "
        "that makes the concept visually intuitive. Use ASCII art, comparison tables, "
        "or structured outlines where helpful."
    ),
    "practical": (
        "Add a 'Hands-On Practice' subsection with 2–3 concrete coding exercises or "
        "mini-projects the learner can do right now to solidify the concept."
    ),
    "research": (
        "Add a 'Deep Dive' subsection citing 2–3 landmark papers or textbook chapters "
        "for this topic. Briefly explain what each contributes to the field."
    ),
    "interview": (
        "Add an 'Interview Prep' subsection with 3–5 common interview questions on "
        "this topic, including concise model answers."
    ),
    "project": (
        "Add a 'Real-World Application' subsection describing how this concept is used "
        "in a specific production system or open-source project, with a link if possible."
    ),
}

DEFAULT_STYLE = "practical"

# ── System prompts ─────────────────────────────────────────────────────────────

_SHELL_SYSTEM = """\
You are an expert AI/ML educator. Create structured learning content for technical topics.
Return only valid JSON, no markdown fences, no extra text.
"""

_SECTION_SYSTEM = """\
You are an expert AI/ML educator. Write clear, accurate, and engaging technical content.
Use markdown formatting (headers, code blocks, bullet points) for readability.
"""

_QUIZ_SYSTEM = """\
You are an expert AI/ML educator. Write multiple-choice quiz questions that test deep
understanding, not just memorization. Return only valid JSON.
"""


# ── Service ───────────────────────────────────────────────────────────────────

class ArtifactService:
    """
    Three-stage lazy content generation using the typed relational artifact tables.

    Stage 1 — Shell: ArtifactShell row with overview + ordered section list
    Stage 2 — Section: ArtifactSection row with base_content + style_overlays dict
    Stage 3 — Quiz: Quiz row with JSONB questions array

    Redis (L1) caches hot content by cache_key for 24 h.
    All content is shared globally — generated once, used by all users.
    """

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _redis_key(self, key: str) -> str:
        return f"artifact:{key}"

    async def _redis_get(self, key: str) -> str | None:
        val = await cache_service.get(self._redis_key(key))
        if val is None:
            return None
        return val if isinstance(val, str) else json.dumps(val)

    async def _redis_set(self, key: str, value: str) -> None:
        await cache_service.set(self._redis_key(key), value, ttl=settings.CACHE_TTL_HOT)

    # ── Stage 1: Shell ────────────────────────────────────────────────────────

    async def get_or_generate_shell(
        self, db: AsyncSession, topic_slug: str
    ) -> dict:
        """Return or generate the artifact shell for a topic (dict with overview + sections)."""
        cache_key = f"{topic_slug}/shell"

        # L1: Redis
        cached = await self._redis_get(cache_key)
        if cached:
            return json.loads(cached)

        # L2: PostgreSQL via typed ArtifactShell table
        topic = await topic_graph_service.get_by_slug(db, topic_slug)
        shell_row = await self._load_shell_row(db, topic.id)
        if shell_row:
            data = self._shell_row_to_dict(shell_row)
            await self._redis_set(cache_key, json.dumps(data))
            return data

        # Generate via LLM
        return await self._generate_shell(db, topic, cache_key)

    async def _load_shell_row(self, db: AsyncSession, topic_id) -> ArtifactShell | None:
        result = await db.execute(
            select(ArtifactShell)
            .where(ArtifactShell.topic_id == topic_id)
            .options(selectinload(ArtifactShell.sections))
        )
        return result.scalar_one_or_none()

    def _shell_row_to_dict(self, shell: ArtifactShell) -> dict:
        sections_sorted = sorted(shell.sections, key=lambda s: s.order_index)
        return {
            "overview": shell.overview or "",
            "sections": [
                {"slug": s.section_slug, "title": s.section_title}
                for s in sections_sorted
            ],
        }

    async def _generate_shell(
        self, db: AsyncSession, topic: Topic, cache_key: str
    ) -> dict:
        prompt = f"""\
Create a learning artifact shell for the topic: "{topic.name}"

Topic description: {topic.description or "A key topic in AI/Machine Learning."}
Difficulty level: {topic.difficulty}

Return a JSON object with:
- "overview": A 2-3 sentence overview of what the learner will understand after this module
- "sections": An ordered array of 4-6 section objects, each with:
  - "slug": a short kebab-case identifier (e.g. "introduction", "core-concepts")
  - "title": A clear, engaging section title

Return only the JSON object. Example:
{{
  "overview": "By the end of this module...",
  "sections": [
    {{"slug": "introduction", "title": "What is {topic.name}?"}},
    {{"slug": "core-concepts", "title": "Core Concepts"}}
  ]
}}
"""
        try:
            response = await provider_router.route(
                task=TaskType.SHORT_GEN,
                prompt=prompt,
                system_prompt=_SHELL_SYSTEM,
                temperature=0.3,
                max_tokens=512,
                json_mode=True,
            )
            raw = _strip_fences(response.content)
            shell_data = json.loads(raw)

            # Persist to ArtifactShell + ArtifactSection rows
            shell_row = ArtifactShell(
                topic_id=topic.id,
                overview=shell_data.get("overview", ""),
                section_titles=[s["slug"] for s in shell_data.get("sections", [])],
                cache_key=cache_key,
            )
            db.add(shell_row)
            await db.flush()

            for i, sec in enumerate(shell_data.get("sections", [])):
                section_cache_key = f"{topic.slug}/{sec['slug']}/meta"
                db.add(ArtifactSection(
                    shell_id=shell_row.id,
                    section_slug=sec["slug"],
                    section_title=sec["title"],
                    order_index=i,
                    cache_key=section_cache_key,
                ))
            await db.flush()

            await self._redis_set(cache_key, json.dumps(shell_data))
            log.info("Shell generated", topic=topic.slug, tokens=response.total_tokens)
            return shell_data

        except Exception as exc:
            log.error("Shell generation failed", topic=topic.slug, error=str(exc))
            return {
                "overview": f"This module covers {topic.name}, a key concept in AI/ML.",
                "sections": [
                    {"slug": "introduction", "title": "Introduction"},
                    {"slug": "core-concepts", "title": "Core Concepts"},
                    {"slug": "practical-application", "title": "Practical Application"},
                    {"slug": "summary", "title": "Summary & Next Steps"},
                ],
            }

    # ── Stage 2: Section Content ───────────────────────────────────────────────

    async def get_or_generate_section(
        self,
        db: AsyncSession,
        topic_slug: str,
        section_slug: str,
        section_title: str,
        learning_style: str | None = None,
    ) -> dict:
        """
        Return or generate section content.
        Returns {"content": str, "has_overlay": bool, "degraded": bool}
        """
        topic = await topic_graph_service.get_by_slug(db, topic_slug)
        section_row = await self._load_section_row(db, topic.id, section_slug)

        # --- Base content ---
        base_content = section_row.base_content if section_row else None
        if not base_content:
            base_cache_key = f"{topic_slug}/{section_slug}/base"
            cached = await self._redis_get(base_cache_key)
            if cached:
                base_content = cached
            else:
                base_content = await self._generate_base_content(
                    db, topic, section_row, section_slug, section_title
                )

        if not base_content:
            return {"content": "Content is being generated. Please try again shortly.", "has_overlay": False, "degraded": True}

        # --- Style overlay ---
        should_add_overlay = (
            learning_style
            and learning_style != DEFAULT_STYLE
            and learning_style in STYLE_PROMPTS
        )

        if should_add_overlay:
            assert learning_style is not None
            overlay_key = f"style_{learning_style}"
            section_row = section_row or await self._load_section_row(db, topic.id, section_slug)
            overlay = (
                section_row.style_overlays.get(overlay_key)
                if section_row and section_row.style_overlays
                else None
            )

            if not overlay:
                redis_overlay_key = f"{topic_slug}/{section_slug}/{overlay_key}"
                cached_overlay = await self._redis_get(redis_overlay_key)
                if cached_overlay:
                    overlay = cached_overlay
                else:
                    overlay = await self._generate_style_overlay(
                        db, topic, section_row, section_slug, section_title,
                        base_content, learning_style
                    )

            if overlay:
                merged = base_content + "\n\n---\n\n" + overlay
                return {"content": merged, "has_overlay": True, "degraded": False}
            else:
                return {"content": base_content, "has_overlay": False, "degraded": True}

        return {"content": base_content, "has_overlay": False, "degraded": False}

    async def _load_section_row(
        self, db: AsyncSession, topic_id, section_slug: str
    ) -> ArtifactSection | None:
        result = await db.execute(
            select(ArtifactSection)
            .join(ArtifactShell, ArtifactSection.shell_id == ArtifactShell.id)
            .where(
                ArtifactShell.topic_id == topic_id,
                ArtifactSection.section_slug == section_slug,
            )
        )
        return result.scalar_one_or_none()

    async def _generate_base_content(
        self,
        db: AsyncSession,
        topic: Topic,
        section_row: ArtifactSection | None,
        section_slug: str,
        section_title: str,
    ) -> str | None:
        prompt = f"""\
Write a comprehensive learning section for an AI/ML course.

Topic: {topic.name}
Section: {section_title}
Difficulty: {topic.difficulty}

Write 400-600 words of clear, well-structured markdown content for this section.
Include:
- A brief intro sentence
- 2-4 key concepts explained clearly
- At least one concrete example or analogy
- A code snippet if relevant (Python)
- A 1-sentence takeaway at the end

Use markdown headers (##, ###), bullet points, and code blocks (```python) where appropriate.
"""
        try:
            response = await provider_router.route(
                task=TaskType.MEDIUM_GEN,
                prompt=prompt,
                system_prompt=_SECTION_SYSTEM,
                temperature=0.4,
                max_tokens=1024,
            )
            content = response.content.strip()

            # Persist to ArtifactSection.base_content
            if section_row:
                section_row.base_content = content
                await db.flush()
            else:
                # Section row may not exist if shell was generated differently — create it
                shell_result = await db.execute(
                    select(ArtifactShell).where(ArtifactShell.topic_id == topic.id)
                )
                shell_row = shell_result.scalar_one_or_none()
                if shell_row:
                    db.add(ArtifactSection(
                        shell_id=shell_row.id,
                        section_slug=section_slug,
                        section_title=section_title,
                        base_content=content,
                        order_index=0,
                        cache_key=f"{topic.slug}/{section_slug}/meta",
                    ))
                    await db.flush()

            # Warm Redis
            await self._redis_set(f"{topic.slug}/{section_slug}/base", content)
            log.info("Section base generated", topic=topic.slug, section=section_slug, tokens=response.total_tokens)
            return content
        except Exception as exc:
            log.error("Section base generation failed", topic=topic.slug, section=section_slug, error=str(exc))
            return None

    async def _generate_style_overlay(
        self,
        db: AsyncSession,
        topic: Topic,
        section_row: ArtifactSection | None,
        section_slug: str,
        section_title: str,
        base_content: str,
        learning_style: str,
    ) -> str | None:
        style_instruction = STYLE_PROMPTS[learning_style]
        prompt = f"""\
You have this learning content about "{section_title}" in the topic "{topic.name}":

---
{base_content[:800]}
---

{style_instruction}

Write only the new subsection content (not the original content). Use markdown.
Keep it concise — 150-250 words maximum.
"""
        try:
            response = await provider_router.route(
                task=TaskType.SHORT_GEN,
                prompt=prompt,
                system_prompt=_SECTION_SYSTEM,
                temperature=0.4,
                max_tokens=512,
            )
            overlay = response.content.strip()
            overlay_key = f"style_{learning_style}"

            # Persist to ArtifactSection.style_overlays JSONB dict
            if section_row:
                overlays = dict(section_row.style_overlays or {})
                overlays[overlay_key] = overlay
                section_row.style_overlays = overlays
                await db.flush()

            # Warm Redis
            await self._redis_set(f"{topic.slug}/{section_slug}/{overlay_key}", overlay)
            log.info("Style overlay generated", topic=topic.slug, section=section_slug, style=learning_style)
            return overlay
        except Exception as exc:
            log.error("Style overlay generation failed", error=str(exc))
            return None

    # ── Stage 3: Quiz ─────────────────────────────────────────────────────────

    async def get_or_generate_quiz(
        self, db: AsyncSession, topic_slug: str, section_slug: str, section_title: str
    ) -> list[dict]:
        """Return or generate quiz questions, persisting to the Quiz table."""
        topic = await topic_graph_service.get_by_slug(db, topic_slug)
        section_row = await self._load_section_row(db, topic.id, section_slug)

        # Check Quiz row
        if section_row:
            quiz_result = await db.execute(
                select(Quiz).where(Quiz.section_id == section_row.id)
            )
            quiz_row = quiz_result.scalar_one_or_none()
            if quiz_row and quiz_row.questions:
                # Warm Redis and return
                cache_key = f"{topic_slug}/{section_slug}/quiz"
                await self._redis_set(cache_key, json.dumps(quiz_row.questions))
                return quiz_row.questions

        # L1: Redis
        cache_key = f"{topic_slug}/{section_slug}/quiz"
        cached = await self._redis_get(cache_key)
        if cached:
            return json.loads(cached)

        # Generate
        return await self._generate_quiz(db, topic, section_row, section_slug, section_title, cache_key)

    async def _generate_quiz(
        self,
        db: AsyncSession,
        topic: Topic,
        section_row: ArtifactSection | None,
        section_slug: str,
        section_title: str,
        cache_key: str,
    ) -> list[dict]:
        prompt = f"""\
Create 5 multiple-choice quiz questions for this AI/ML learning section.

Topic: {topic.name}
Section: {section_title}

Return a JSON array of 5 objects, each with:
- "question": The question text
- "options": Array of exactly 4 answer strings (A, B, C, D)
- "correct_index": Index of the correct answer (0-3)
- "explanation": 1-2 sentence explanation of why the answer is correct

Test conceptual understanding, not memorization. Make distractors plausible.
Return only the JSON array.
"""
        try:
            response = await provider_router.route(
                task=TaskType.SHORT_GEN,
                prompt=prompt,
                system_prompt=_QUIZ_SYSTEM,
                temperature=0.5,
                max_tokens=1024,
                json_mode=True,
            )
            raw = _strip_fences(response.content)
            questions = json.loads(raw)
            if not isinstance(questions, list):
                raise ValueError("Quiz response is not a list")

            # Persist to Quiz table
            if section_row:
                quiz_result = await db.execute(
                    select(Quiz).where(Quiz.section_id == section_row.id)
                )
                existing_quiz = quiz_result.scalar_one_or_none()
                if existing_quiz:
                    existing_quiz.questions = questions
                else:
                    db.add(Quiz(
                        section_id=section_row.id,
                        questions=questions,
                        cache_key=cache_key,
                    ))
                await db.flush()

            await self._redis_set(cache_key, json.dumps(questions))
            log.info("Quiz generated", topic=topic.slug, section=section_slug, questions=len(questions))
            return questions

        except Exception as exc:
            log.error("Quiz generation failed", topic=topic.slug, section=section_slug, error=str(exc))
            return []


# ── Helpers ───────────────────────────────────────────────────────────────────

def _strip_fences(text: str) -> str:
    """Strip markdown code fences from LLM output."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text


artifact_service = ArtifactService()
