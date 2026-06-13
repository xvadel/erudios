from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import auth, topics, resources, health

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(topics.router, prefix="/topics", tags=["topics"])
api_router.include_router(resources.router, prefix="/resources", tags=["resources"])
api_router.include_router(health.router, prefix="/health", tags=["system"])
