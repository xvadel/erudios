"""SQLAlchemy models package.

Import all models here so Alembic can discover them.
"""
from app.models.user import User
from app.models.topic import Topic, TopicDependency
from app.models.resource import Resource, TrustedDomain, ResourceRefreshLog
from app.models.curriculum import Curriculum, Module
from app.models.artifact import ArtifactShell, ArtifactSection, Quiz
from app.models.content import GeneratedContent
from app.models.progress import LearningProgress
from app.models.chat import ChatSession, ChatMessage
from app.models.provider import ProviderUsage

__all__ = [
    "User",
    "Topic",
    "TopicDependency",
    "Resource",
    "TrustedDomain",
    "ResourceRefreshLog",
    "Curriculum",
    "Module",
    "ArtifactShell",
    "ArtifactSection",
    "Quiz",
    "GeneratedContent",
    "LearningProgress",
    "ChatSession",
    "ChatMessage",
    "ProviderUsage",
]
