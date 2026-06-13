from __future__ import annotations

from collections import defaultdict, deque

import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.topic import Topic, TopicDependency
from app.core.exceptions import NotFoundError

log = structlog.get_logger()


class TopicGraphService:
    """
    Core service for the AI topic taxonomy and dependency graph.
    Powers the "What to learn next?" feature.
    """

    async def get_all_roots(self, db: AsyncSession) -> list[Topic]:
        """Get top-level AI domains (no parent)."""
        result = await db.execute(
            select(Topic)
            .where(Topic.parent_id.is_(None))
            .options(selectinload(Topic.children))
            .order_by(Topic.name)
        )
        return list(result.scalars().all())

    async def get_by_slug(self, db: AsyncSession, slug: str) -> Topic:
        """Get a topic by its slug. Raises NotFoundError if not found."""
        result = await db.execute(
            select(Topic)
            .where(Topic.slug == slug)
            .options(
                selectinload(Topic.children),
                selectinload(Topic.prerequisites)
                .selectinload(TopicDependency.prerequisite)
                .selectinload(Topic.children),
                selectinload(Topic.dependents)
                .selectinload(TopicDependency.dependent)
                .selectinload(Topic.children),
            )
        )
        topic = result.scalar_one_or_none()
        if topic is None:
            raise NotFoundError(f"Topic '{slug}' not found")
        return topic

    async def get_children(self, db: AsyncSession, parent_slug: str) -> list[Topic]:
        """Get direct children of a topic."""
        parent = await self.get_by_slug(db, parent_slug)
        result = await db.execute(
            select(Topic)
            .where(Topic.parent_id == parent.id)
            .options(selectinload(Topic.children))
            .order_by(Topic.name)
        )
        return list(result.scalars().all())

    async def get_prerequisites(self, db: AsyncSession, topic_slug: str) -> list[dict]:
        """Get all prerequisites for a topic with reasons."""
        topic = await self.get_by_slug(db, topic_slug)
        prereqs = []
        for dep in topic.prerequisites:
            prereqs.append({
                "topic": dep.prerequisite,
                "reason": dep.reason,
            })
        return prereqs

    async def get_whats_next(
        self,
        db: AsyncSession,
        topic_slug: str,
        completed_slugs: list[str] | None = None,
    ) -> list[dict]:
        """
        The core "What to learn next?" engine.

        Given a topic the user just completed, returns the next unlocked topics
        with explanations of why each is recommended.

        completed_slugs: list of slugs the user has already completed.
        """
        completed = set(completed_slugs or [topic_slug])

        # Get all topics that have the given topic as a prerequisite
        result = await db.execute(
            select(TopicDependency)
            .join(Topic, Topic.id == TopicDependency.prerequisite_id)
            .where(Topic.slug == topic_slug)
            .options(
                selectinload(TopicDependency.dependent).selectinload(Topic.children)
            )
        )
        direct_dependents = list(result.scalars().all())

        recommendations = []
        for dep in direct_dependents:
            dependent_topic = dep.dependent

            # Check if all prerequisites of this dependent are completed
            prereq_result = await db.execute(
                select(TopicDependency)
                .join(Topic, Topic.id == TopicDependency.prerequisite_id)
                .where(TopicDependency.dependent_id == dependent_topic.id)
                .options(selectinload(TopicDependency.prerequisite))
            )
            all_prereqs = list(prereq_result.scalars().all())
            all_satisfied = all(p.prerequisite.slug in completed for p in all_prereqs)

            if all_satisfied and dependent_topic.slug not in completed:
                recommendations.append({
                    "topic": dependent_topic,
                    "reason": dep.reason,
                    "readiness": "ready",
                })

        # Sort: prefer topics where more prerequisites are satisfied
        recommendations.sort(key=lambda x: x["topic"].difficulty)
        return recommendations

    async def get_learning_path(
        self,
        db: AsyncSession,
        root_slug: str,
        target_slug: str | None = None,
    ) -> list[Topic]:
        """
        Compute topological order for all topics under a root topic
        (or up to a specific target topic).
        Uses Kahn's algorithm on the dependency graph.
        """
        # Get all topics under this root
        topics = await self._get_subtree(db, root_slug)
        if not topics:
            return []

        topic_map = {t.id: t for t in topics}
        slug_map = {t.slug: t for t in topics}

        # Build adjacency: prerequisite → dependents (within subtree only)
        in_degree: dict = defaultdict(int)
        adjacency: dict = defaultdict(list)

        # Get all dependencies within this subtree
        topic_ids = list(topic_map.keys())
        if not topic_ids:
            return []

        result = await db.execute(
            select(TopicDependency).where(
                TopicDependency.prerequisite_id.in_(topic_ids),
                TopicDependency.dependent_id.in_(topic_ids),
            )
        )
        deps = list(result.scalars().all())

        for dep in deps:
            adjacency[dep.prerequisite_id].append(dep.dependent_id)
            in_degree[dep.dependent_id] += 1

        # Kahn's algorithm (BFS topological sort)
        queue = deque(
            tid for tid in topic_ids if in_degree.get(tid, 0) == 0
        )
        ordered = []
        while queue:
            current = queue.popleft()
            if current in topic_map:
                ordered.append(topic_map[current])
            for neighbor in adjacency[current]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        return ordered

    async def _get_subtree(self, db: AsyncSession, root_slug: str) -> list[Topic]:
        """Get all topics in the subtree rooted at root_slug (BFS)."""
        root = await self.get_by_slug(db, root_slug)
        all_topics = [root]
        queue = deque([root.id])
        visited = {root.id}

        while queue:
            parent_id = queue.popleft()
            result = await db.execute(
                select(Topic)
                .where(Topic.parent_id == parent_id)
                .options(selectinload(Topic.children))
            )
            children = list(result.scalars().all())
            for child in children:
                if child.id not in visited:
                    visited.add(child.id)
                    all_topics.append(child)
                    queue.append(child.id)

        return all_topics

    async def search(self, db: AsyncSession, query: str, limit: int = 10) -> list[Topic]:
        """Simple text search across topic names and descriptions."""
        result = await db.execute(
            select(Topic)
            .where(
                Topic.name.ilike(f"%{query}%")
                | Topic.description.ilike(f"%{query}%")
            )
            .options(selectinload(Topic.children))
            .limit(limit)
        )
        return list(result.scalars().all())


topic_graph_service = TopicGraphService()
