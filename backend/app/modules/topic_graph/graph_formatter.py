from __future__ import annotations

import uuid
from typing import Any
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.topic import Topic, TopicDependency
from app.models.progress import LearningProgress
from app.models.curriculum import Module
from app.modules.recommendation.service import recommendation_service

class GraphNodeData(BaseModel):
    slug: str
    name: str
    difficulty: str
    estimated_hours: float
    description: str | None = None
    mastery_score: float = 0.0
    status: str  # locked | unlocked | in_progress | mastered | weak | suggested


class GraphNode(BaseModel):
    id: str
    data: GraphNodeData
    position: dict[str, float] = {"x": 0.0, "y": 0.0}


class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    animated: bool = False


class ReactFlowGraph(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]


class GraphFormatter:
    """
    Formats the hierarchical AI taxonomy / subtrees into React Flow-compatible
    node and edge structures, applying contextual user progress states.
    """

    async def build_user_graph(
        self, db: AsyncSession, root_topic: Topic, user_id: uuid.UUID
    ) -> ReactFlowGraph:
        # 1. Fetch all topics in the root subtree
        from app.modules.topic_graph.service import topic_graph_service
        all_topics = await topic_graph_service._get_subtree(db, root_topic.slug)
        if not all_topics:
            return ReactFlowGraph(nodes=[], edges=[])

        topic_map = {t.id: t for t in all_topics}
        topic_ids = list(topic_map.keys())

        # 2. Fetch learning progress for these topics
        progress_result = await db.execute(
            select(LearningProgress)
            .join(Module, LearningProgress.module_id == Module.id)
            .where(
                LearningProgress.user_id == user_id,
                Module.topic_id.in_(topic_ids)
            )
        )
        progresses = progress_result.scalars().all()
        # Map topic_id -> mastery_score
        mastery_map: dict[uuid.UUID, float] = {}
        progress_map: dict[uuid.UUID, LearningProgress] = {}
        for p in progresses:
            if p.module:
                mastery_map[p.module.topic_id] = p.mastery_score
                progress_map[p.module.topic_id] = p

        # 3. Load dependencies within this subtree
        deps_result = await db.execute(
            select(TopicDependency).where(
                TopicDependency.prerequisite_id.in_(topic_ids),
                TopicDependency.dependent_id.in_(topic_ids),
            )
        )
        deps = deps_result.scalars().all()

        # 4. Determine suggested topics (from RecommendationEngine)
        recs = await recommendation_service.get_recommendations(db, user_id, limit=3)
        suggested_slugs = {r.topic.slug for r in recs}

        # 5. Build nodes
        nodes = []
        for topic in all_topics:
            mastery = mastery_map.get(topic.id, 0.0)
            
            # Determine node status
            status = "unlocked"
            
            # Check prerequisites mastery
            prereq_deps = [d for d in topic.prerequisites if d.prerequisite_id in topic_map]
            has_unmet_prereq = False
            for d in prereq_deps:
                prereq_mastery = mastery_map.get(d.prerequisite_id, 0.0)
                if prereq_mastery < 60.0:
                    has_unmet_prereq = True
                    break

            # Calculate actual status
            if has_unmet_prereq:
                status = "locked"
            elif topic.slug in suggested_slugs:
                status = "suggested"
            elif topic.id in mastery_map:
                p = progress_map[topic.id]
                from app.modules.mastery.service import mastery_service
                review_status = mastery_service.get_review_status(p)
                
                if review_status == "overdue" or review_status == "due":
                    status = "weak"
                elif mastery >= 80.0:
                    status = "mastered"
                else:
                    status = "in_progress"

            nodes.append(
                GraphNode(
                    id=topic.slug,
                    data=GraphNodeData(
                        slug=topic.slug,
                        name=topic.name,
                        difficulty=topic.difficulty,
                        estimated_hours=topic.estimated_hours,
                        description=topic.description,
                        mastery_score=mastery,
                        status=status,
                    )
                )
            )

        # 6. Build edges
        edges = []
        for dep in deps:
            prereq_topic = topic_map.get(dep.prerequisite_id)
            dependent_topic = topic_map.get(dep.dependent_id)
            if prereq_topic and dependent_topic:
                # Highlight edges leading to suggested/in_progress topics
                is_active = (mastery_map.get(prereq_topic.id, 0.0) >= 60.0)
                edges.append(
                    GraphEdge(
                        id=f"edge-{prereq_topic.slug}-{dependent_topic.slug}",
                        source=prereq_topic.slug,
                        target=dependent_topic.slug,
                        animated=is_active,
                    )
                )

        return ReactFlowGraph(nodes=nodes, edges=edges)


graph_formatter = GraphFormatter()
