from __future__ import annotations

import json

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.content_cache import content_cache
from app.providers.llms.router import provider_router
from app.providers.llms.budget import TaskType
from app.modules.topic_graph.service import topic_graph_service
from app.core.exceptions import NotFoundError

log = structlog.get_logger()


# ── Default learning style (overlay skipped for this value if content == base) ─

DEFAULT_STYLE = "practical"

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
    Three-stage lazy content generation for topic learning artifacts.

    Stage 1 — Shell: overview + section titles (~200 tokens, once per topic)
    Stage 2 — Section content: base markdown (~600 tokens, once per topic/section)
               + optional style overlay (~400 tokens, once per topic/section/style)
    Stage 3 — Quiz: 5 MCQ questions (~400 tokens, once per topic/section)

    All content is shared globally — generated once, cached for all users.
    """

    # ── Stage 1: Shell ────────────────────────────────────────────────────────

    async def get_or_generate_shell(
        self, db: AsyncSession, topic_slug: str
    ) -> dict:
        """Return or generate the artifact shell for a topic."""
        cache_key = f"{topic_slug}/shell"
        cached = await content_cache.get(db, cache_key)
        if cached:
            return json.loads(cached)

        topic = await topic_graph_service.get_by_slug(db, topic_slug)

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

            await content_cache.set(
                db=db,
                cache_key=cache_key,
                content=json.dumps(shell_data),
                provider_used=response.provider,
                model_used=response.model,
                tokens_input=response.tokens_input,
                tokens_output=response.tokens_output,
            )
            log.info("Shell generated", topic=topic_slug, tokens=response.total_tokens)
            return shell_data

        except Exception as exc:
            log.error("Shell generation failed", topic=topic_slug, error=str(exc))
            # Return a minimal fallback shell
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
        If learning_style is provided and is not DEFAULT_STYLE, appends a style overlay.
        Returns {"content": str, "has_overlay": bool, "degraded": bool}
        """
        base_key = f"{topic_slug}/{section_slug}/base"
        base_content = await content_cache.get(db, base_key)

        if not base_content:
            base_content = await self._generate_base_content(
                db, topic_slug, section_slug, section_title, base_key
            )

        if not base_content:
            return {"content": "Content is being generated. Please try again shortly.", "has_overlay": False, "degraded": True}

        # Style overlay: only if (a) non-default style and (b) cache miss
        should_add_overlay = (
            learning_style
            and learning_style != DEFAULT_STYLE
            and learning_style in STYLE_PROMPTS
        )

        if should_add_overlay:
            assert learning_style is not None
            overlay_key = f"{topic_slug}/{section_slug}/style_{learning_style}"
            overlay = await content_cache.get(db, overlay_key)

            if not overlay:
                overlay = await self._generate_style_overlay(
                    db, topic_slug, section_slug, section_title, base_content, learning_style, overlay_key
                )

            if overlay:
                merged = base_content + "\n\n---\n\n" + overlay
                return {"content": merged, "has_overlay": True, "degraded": False}
            else:
                # Overlay generation failed — return base with degraded flag
                return {"content": base_content, "has_overlay": False, "degraded": True}

        return {"content": base_content, "has_overlay": False, "degraded": False}

    async def _generate_base_content(
        self,
        db: AsyncSession,
        topic_slug: str,
        section_slug: str,
        section_title: str,
        cache_key: str,
    ) -> str | None:
        topic = await topic_graph_service.get_by_slug(db, topic_slug)

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
            await content_cache.set(
                db=db,
                cache_key=cache_key,
                content=content,
                provider_used=response.provider,
                model_used=response.model,
                tokens_input=response.tokens_input,
                tokens_output=response.tokens_output,
            )
            log.info("Section base generated", topic=topic_slug, section=section_slug, tokens=response.total_tokens)
            return content
        except Exception as exc:
            log.error("Section base generation failed", topic=topic_slug, section=section_slug, error=str(exc))
            return None

    async def _generate_style_overlay(
        self,
        db: AsyncSession,
        topic_slug: str,
        section_slug: str,
        section_title: str,
        base_content: str,
        learning_style: str,
        cache_key: str,
    ) -> str | None:
        topic = await topic_graph_service.get_by_slug(db, topic_slug)
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
            await content_cache.set(
                db=db,
                cache_key=cache_key,
                content=overlay,
                provider_used=response.provider,
                model_used=response.model,
                tokens_input=response.tokens_input,
                tokens_output=response.tokens_output,
            )
            log.info("Style overlay generated", topic=topic_slug, section=section_slug, style=learning_style)
            return overlay
        except Exception as exc:
            log.error("Style overlay generation failed", error=str(exc))
            return None

    # ── Stage 3: Quiz ─────────────────────────────────────────────────────────

    async def get_or_generate_quiz(
        self, db: AsyncSession, topic_slug: str, section_slug: str, section_title: str
    ) -> list[dict]:
        """Return or generate quiz questions for a section."""
        cache_key = f"{topic_slug}/{section_slug}/quiz"
        cached = await content_cache.get(db, cache_key)
        if cached:
            return json.loads(cached)

        topic = await topic_graph_service.get_by_slug(db, topic_slug)

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

            await content_cache.set(
                db=db,
                cache_key=cache_key,
                content=json.dumps(questions),
                provider_used=response.provider,
                model_used=response.model,
                tokens_input=response.tokens_input,
                tokens_output=response.tokens_output,
            )
            log.info("Quiz generated", topic=topic_slug, section=section_slug, questions=len(questions))
            return questions

        except Exception as exc:
            log.error("Quiz generation failed", topic=topic_slug, section=section_slug, error=str(exc))
            return []


# ── Helpers ───────────────────────────────────────────────────────────────────

def _strip_fences(text: str) -> str:
    """Strip markdown code fences from LLM output."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        # Remove first line (```json or ```) and last line (```)
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text


artifact_service = ArtifactService()
