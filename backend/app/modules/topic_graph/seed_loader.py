from __future__ import annotations

import json
import os
from pathlib import Path

import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.topic import Topic, TopicDependency
from app.models.resource import TrustedDomain
from app.config import settings

log = structlog.get_logger()

SEED_DIR = Path(__file__).parent.parent.parent.parent / "seed"


async def seed_if_empty(db: AsyncSession) -> None:
    """Load seed data into database only if topics table is empty."""
    count = await db.scalar(select(func.count()).select_from(Topic))
    if count and count > 0:
        log.info("Seed data already loaded", topic_count=count)
        return

    log.info("Loading seed data into database...")
    await _seed_taxonomy(db)
    await _seed_trusted_sources(db)
    await db.commit()
    log.info("✅ Seed data loaded successfully")


async def _seed_taxonomy(db: AsyncSession) -> None:
    taxonomy_path = SEED_DIR / "ai_taxonomy.json"
    deps_path = SEED_DIR / "dependency_graph.json"

    with open(taxonomy_path, encoding="utf-8") as f:
        taxonomy = json.load(f)

    # First pass: create all topics (without parents to avoid FK issues)
    slug_to_id: dict[str, object] = {}
    for item in taxonomy["topics"]:
        topic = Topic(
            slug=item["slug"],
            name=item["name"],
            description=item.get("description"),
            difficulty=item.get("difficulty", "intermediate"),
            estimated_hours=item.get("estimated_hours", 2.0),
            is_seed=True,
        )
        db.add(topic)
        await db.flush()
        slug_to_id[item["slug"]] = topic.id

    # Second pass: set parent IDs
    for item in taxonomy["topics"]:
        if item.get("parent_slug"):
            parent_id = slug_to_id.get(item["parent_slug"])
            if parent_id:
                result = await db.execute(
                    select(Topic).where(Topic.slug == item["slug"])
                )
                topic = result.scalar_one()
                topic.parent_id = parent_id

    await db.flush()

    # Load dependency graph
    with open(deps_path, encoding="utf-8") as f:
        deps_data = json.load(f)

    for dep in deps_data["dependencies"]:
        prereq_id = slug_to_id.get(dep["prerequisite"])
        dependent_id = slug_to_id.get(dep["dependent"])
        if prereq_id and dependent_id:
            db.add(
                TopicDependency(
                    prerequisite_id=prereq_id,
                    dependent_id=dependent_id,
                    reason=dep.get("reason"),
                )
            )

    await db.flush()
    log.info("Topic taxonomy seeded", count=len(taxonomy["topics"]))


async def _seed_trusted_sources(db: AsyncSession) -> None:
    sources_path = SEED_DIR / "trusted_sources.json"
    with open(sources_path, encoding="utf-8") as f:
        data = json.load(f)

    for item in data["trusted_domains"]:
        db.add(
            TrustedDomain(
                domain=item["domain"],
                base_trust_score=item.get("base_trust_score", 70.0),
                category=item.get("category", "blog"),
                notes=item.get("notes"),
            )
        )

    await db.flush()
    log.info("Trusted sources seeded", count=len(data["trusted_domains"]))
