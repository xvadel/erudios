"""
Centralized Pydantic schemas package.
All API request/response models are defined here and imported by API routers.
"""
from app.schemas.user import UserResponse, RegisterRequest, LoginRequest, TokenResponse, UpdateProfileRequest
from app.schemas.topic import TopicOut, TopicTreeNode, DependencyOut, WhatsNextResponse
from app.schemas.resource import ResourceOut
from app.schemas.curriculum import ModuleOut, CurriculumOut, CurriculumSummary
from app.schemas.artifact import SectionInfo, ShellOut, SectionOut, QuizQuestion, QuizOut
from app.schemas.progress import (
    CompleteModuleRequest, QuizResultRequest, ProgressOut, CurriculumProgressOut
)
from app.schemas.chat import (
    ChatSessionOut, ChatMessageOut, ChatMessageCreate, ChatSessionCreate
)

__all__ = [
    # User / Auth
    "UserResponse", "RegisterRequest", "LoginRequest", "TokenResponse", "UpdateProfileRequest",
    # Topics
    "TopicOut", "TopicTreeNode", "DependencyOut", "WhatsNextResponse",
    # Resources
    "ResourceOut",
    # Curriculum
    "ModuleOut", "CurriculumOut", "CurriculumSummary",
    # Artifacts
    "SectionInfo", "ShellOut", "SectionOut", "QuizQuestion", "QuizOut",
    # Progress
    "CompleteModuleRequest", "QuizResultRequest", "ProgressOut", "CurriculumProgressOut",
    # Chat
    "ChatSessionOut", "ChatMessageOut", "ChatMessageCreate", "ChatSessionCreate",
]
