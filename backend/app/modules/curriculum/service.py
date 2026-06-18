from __future__ import annotations

import json
import uuid
from typing import TYPE_CHECKING

import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.curriculum import Curriculum, Module
from app.models.topic import Topic
from app.modules.topic_graph.service import topic_graph_service
from app.services.content_cache import content_cache
from app.providers.llms.router import provider_router
from app.providers.llms.budget import TaskType
from app.core.exceptions import NotFoundError, ProviderExhaustedError

if TYPE_CHECKING:
    from app.models.user import User

log = structlog.get_logger()


# ── Prompts ───────────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """\
You are a curriculum designer specializing in AI and Machine Learning education.
Your job is to create clear, motivating module descriptions for a personalized
learning curriculum. Always return valid JSON and nothing else.
"""


def _build_prompt(
    topics: list[Topic],
    level: str,
    learning_style: str,
    goal: str,
) -> str:
    style_descriptions = {
        "visual": "prefers diagrams, mental models, and visual explanations",
        "practical": "learns best by building projects and running code",
        "research": "wants deep theoretical understanding and academic papers",
        "interview": "focused on interview preparation and problem-solving patterns",
        "project": "motivated by real-world applications and end-to-end projects",
    }
    goal_descriptions = {
        "job": "getting a job in AI/ML",
        "research": "doing academic research",
        "startup": "building an AI-powered startup",
        "academic": "academic study",
        "general": "general knowledge and exploration",
    }

    style_desc = style_descriptions.get(learning_style, learning_style)
    goal_desc = goal_descriptions.get(goal, goal)

    topic_list = "\n".join(
        f"{i + 1}. {t.name} (slug: {t.slug}, difficulty: {t.difficulty})"
        + (f"\n   Description: {t.description}" if t.description else "")
        for i, t in enumerate(topics)
    )

    return f"""\
Create a personalized learning curriculum for the following student profile:
- Skill level: {level}
- Learning style: {style_desc}
- Goal: {goal_desc}

The curriculum must cover these topics IN THIS EXACT ORDER (they are already \
topologically sorted by prerequisites):

{topic_list}

For each topic, return a JSON object with:
- "title": A short, engaging module title (different from the raw topic name)
- "description": 1-2 sentences explaining what the student will learn and why it matters
- "why_next": 1 sentence explaining why this follows the previous module \
(for the first module, explain why it's the starting point)
- "estimated_hours": estimated study hours (number, can differ from the default)
- "difficulty": the difficulty level of this module for this student \
(may differ from topic difficulty based on their level)

Return a JSON array with exactly {len(topics)} objects, one per topic.
Do not include any text before or after the JSON array.

Example format:
[
  {{
    "title": "Module title here",
    "description": "What the student learns and why it matters.",
    "why_next": "This is the foundation for everything that follows.",
    "estimated_hours": 3.0,
    "difficulty": "beginner"
  }}
]
"""


# ── Service ───────────────────────────────────────────────────────────────────

class CurriculumService:
    """
    Generates and caches personalized learning curricula.

    Uses a single batched LLM call to generate all module descriptions at once,
    then stores the result in GeneratedContent for cross-user cache sharing.
    """

    def _cache_key(
        self, root_slug: str, level: str, learning_style: str, goal: str
    ) -> str:
        return f"curriculum:{root_slug}:{level}:{learning_style}:{goal}"

    async def get_or_create(
        self,
        db: AsyncSession,
        user: "User",
        root_topic_slug: str,
    ) -> Curriculum:
        """
        Return cached curriculum for this user+topic+profile combo,
        or generate a new one. If the same profile+topic was already generated
        for another user, the LLM-generated module descriptions are reused
        from GeneratedContent — only the Curriculum + Module rows are new.
        """
        cache_key = self._cache_key(
            root_topic_slug, user.level, user.learning_style, user.goal
        )

        # Check if this user already has a curriculum for this topic+profile
        existing = await self._find_existing(db, user.id, root_topic_slug, user.level, user.learning_style, user.goal)
        if existing:
            log.info("Curriculum cache hit (user)", user_id=user.id, topic=root_topic_slug)
            return existing

        # Check if another user already generated the same profile+topic combo
        cached_json = await content_cache.get(db, cache_key)
        if cached_json:
            log.info("Curriculum cache hit (shared)", topic=root_topic_slug)
            module_data = json.loads(cached_json)
        else:
            log.info("Generating curriculum", topic=root_topic_slug, user_id=user.id)
            module_data = await self._generate_with_llm(
                db, root_topic_slug, user.level, user.learning_style, user.goal
            )
            # Store for future users with same profile
            llm_response_json = json.dumps(module_data)
            # We'll store via content_cache.set below after the LLM call
            # This is done inside _generate_with_llm

        # Resolve the root topic
        root_topic = await topic_graph_service.get_by_slug(db, root_topic_slug)

        # Get the ordered topic list (same order used in generation)
        ordered_topics = await topic_graph_service.get_learning_path(db, root_topic_slug)
        if not ordered_topics:
            ordered_topics = [root_topic]

        # Build Curriculum + Module rows
        curriculum = Curriculum(
            user_id=user.id,
            root_topic_id=root_topic.id,
            level=user.level,
            learning_style=user.learning_style,
            goal=user.goal,
            cache_key=cache_key,
            module_order=[],
        )
        db.add(curriculum)
        await db.flush()

        # Ensure module_data is a clean list of dicts matching topics
        clean_module_data = []
        if isinstance(module_data, list):
            # If the cache contains a nested list (e.g. list inside list), extract it
            for item in module_data:
                if isinstance(item, list) and any(isinstance(sub, dict) and "title" in sub for sub in item):
                    module_data = item
                    break
            
            for item in module_data:
                if isinstance(item, dict):
                    clean_module_data.append(item)
                else:
                    clean_module_data.append({})
        else:
            clean_module_data = [{} for _ in ordered_topics]

        # Pad or trim to match topic count
        while len(clean_module_data) < len(ordered_topics):
            clean_module_data.append({})
        clean_module_data = clean_module_data[:len(ordered_topics)]

        modules = []
        for i, topic in enumerate(ordered_topics):
            mod_data = clean_module_data[i]
            module = Module(
                curriculum_id=curriculum.id,
                topic_id=topic.id,
                order_index=i,
                title=mod_data.get("title") or topic.name,
                description=mod_data.get("description") or topic.description or "No description available.",
                why_next=mod_data.get("why_next") or ("This is the starting point." if i == 0 else f"Builds on top of previous modules."),
                estimated_hours=float(mod_data.get("estimated_hours") or topic.estimated_hours),
                difficulty=mod_data.get("difficulty") or topic.difficulty,
            )
            db.add(module)
            modules.append(module)

        await db.flush()
        curriculum.module_order = [str(m.id) for m in modules]
        await db.flush()

        log.info(
            "Curriculum created",
            curriculum_id=curriculum.id,
            topic=root_topic_slug,
            module_count=len(modules),
        )
        return await self.get_by_id(db, curriculum.id)

    async def _find_existing(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        root_topic_slug: str,
        level: str,
        learning_style: str,
        goal: str,
    ) -> Curriculum | None:
        """Find an existing curriculum for this user+topic+profile."""
        from sqlalchemy import join
        result = await db.execute(
            select(Curriculum)
            .join(Topic, Curriculum.root_topic_id == Topic.id)
            .where(
                Curriculum.user_id == user_id,
                Topic.slug == root_topic_slug,
                Curriculum.level == level,
                Curriculum.learning_style == learning_style,
                Curriculum.goal == goal,
            )
            .options(selectinload(Curriculum.modules).selectinload(Module.topic))
            .order_by(Curriculum.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def _generate_with_llm(
        self,
        db: AsyncSession,
        root_topic_slug: str,
        level: str,
        learning_style: str,
        goal: str,
    ) -> list[dict]:
        """
        Single batched LLM call that generates all module descriptions at once.
        Returns parsed list of module dicts.
        Retries once with a stricter prompt if JSON parsing fails.
        """
        ordered_topics = await topic_graph_service.get_learning_path(db, root_topic_slug)
        if not ordered_topics:
            root = await topic_graph_service.get_by_slug(db, root_topic_slug)
            ordered_topics = [root]

        prompt = _build_prompt(ordered_topics, level, learning_style, goal)

        for attempt in range(2):
            try:
                response = await provider_router.route(
                    task=TaskType.DEEP_GEN,
                    prompt=prompt if attempt == 0 else prompt + "\n\nIMPORTANT: Return ONLY a valid JSON array. No markdown, no explanation, no code blocks.",
                    system_prompt=_SYSTEM_PROMPT,
                    temperature=0.4,
                    max_tokens=2048,
                    json_mode=True,
                )

                # Strip markdown code fences if present
                raw = response.content.strip()
                if raw.startswith("```"):
                    raw = raw.split("```")[1]
                    if raw.startswith("json"):
                        raw = raw[4:]
                    raw = raw.strip()

                module_data = json.loads(raw)
                if not isinstance(module_data, list):
                    raise ValueError("LLM returned non-array JSON")

                # Pad or trim to match topic count
                while len(module_data) < len(ordered_topics):
                    module_data.append({})
                module_data = module_data[: len(ordered_topics)]

                # Cache the result for cross-user sharing
                cache_key = self._cache_key(root_topic_slug, level, learning_style, goal)
                await content_cache.set(
                    db=db,
                    cache_key=cache_key,
                    content=json.dumps(module_data),
                    provider_used=response.provider,
                    model_used=response.model,
                    tokens_input=response.tokens_input,
                    tokens_output=response.tokens_output,
                )

                log.info(
                    "Curriculum LLM generation complete",
                    topic=root_topic_slug,
                    modules=len(module_data),
                    tokens=response.total_tokens,
                    provider=response.provider,
                )
                return module_data

            except (json.JSONDecodeError, ValueError) as exc:
                if attempt == 0:
                    log.warning("Curriculum JSON parse failed, retrying", error=str(exc))
                    continue
                log.error("Curriculum generation failed after retry", error=str(exc))
                # Fall back to empty module data — titles will use topic names
                return [{} for _ in ordered_topics]
            except Exception as exc:
                log.error("Curriculum generation failed with exception", error=str(exc))
                return [{} for _ in ordered_topics]

        return [{} for _ in ordered_topics]

    async def get_by_id(self, db: AsyncSession, curriculum_id: uuid.UUID) -> Curriculum:
        result = await db.execute(
            select(Curriculum)
            .where(Curriculum.id == curriculum_id)
            .options(
                selectinload(Curriculum.modules).selectinload(Module.topic),
                selectinload(Curriculum.root_topic),
            )
        )
        curriculum = result.scalar_one_or_none()
        if curriculum is None:
            raise NotFoundError(f"Curriculum '{curriculum_id}' not found")
        return curriculum

    async def list_for_user(
        self, db: AsyncSession, user_id: uuid.UUID
    ) -> list[Curriculum]:
        result = await db.execute(
            select(Curriculum)
            .where(Curriculum.user_id == user_id)
            .options(
                selectinload(Curriculum.modules).selectinload(Module.topic),
                selectinload(Curriculum.root_topic),
            )
            .order_by(Curriculum.created_at.desc())
        )
        return list(result.scalars().all())

    async def delete(
        self, db: AsyncSession, curriculum_id: uuid.UUID, user_id: uuid.UUID
    ) -> None:
        result = await db.execute(
            select(Curriculum).where(
                Curriculum.id == curriculum_id,
                Curriculum.user_id == user_id,
            )
        )
        curriculum = result.scalar_one_or_none()
        if curriculum is None:
            raise NotFoundError("Curriculum not found or access denied")
        await db.delete(curriculum)


curriculum_service = CurriculumService()
