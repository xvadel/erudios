from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.api.v1.auth import get_current_user
from app.models.user import User
from app.modules.topic_graph.service import topic_graph_service
from app.modules.topic_graph.graph_formatter import graph_formatter, ReactFlowGraph

router = APIRouter()


@router.get("/{root_slug}", response_model=ReactFlowGraph)
async def get_topic_graph(
    root_slug: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Fetch a React Flow-compatible node-edge dependency graph for the topic subtree
    rooted at root_slug, complete with personalized user learning statuses.
    """
    user: User = await get_current_user(request, db)
    root_topic = await topic_graph_service.get_by_slug(db, root_slug)
    return await graph_formatter.build_user_graph(db, root_topic, user.id)
