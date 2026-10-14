from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import auth, topics, resources, health, curriculum, artifacts, progress, chat, recommendations, analytics, intelligence, graph

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(topics.router, prefix="/topics", tags=["topics"])
api_router.include_router(resources.router, prefix="/resources", tags=["resources"])
api_router.include_router(health.router, prefix="/health", tags=["system"])
api_router.include_router(curriculum.router, prefix="/curriculum", tags=["curriculum"])
api_router.include_router(artifacts.router, prefix="/artifacts", tags=["artifacts"])
api_router.include_router(progress.router, prefix="/progress", tags=["progress"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(recommendations.router, prefix="/recommendations", tags=["recommendations"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
api_router.include_router(intelligence.router, prefix="/intelligence", tags=["intelligence"])
api_router.include_router(graph.router, prefix="/graph", tags=["graph"])


