from __future__ import annotations

import uuid
from pydantic import BaseModel, field_validator


class RegisterRequest(BaseModel):
    username: str
    password: str

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v

    @field_validator("username")
    @classmethod
    def username_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Username cannot be empty")
        return v.strip()


class LoginRequest(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    id: uuid.UUID
    username: str
    name: str
    avatar_url: str | None
    level: str
    learning_style: str
    goal: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class UpdateProfileRequest(BaseModel):
    level: str | None = None
    learning_style: str | None = None
    goal: str | None = None
    name: str | None = None
