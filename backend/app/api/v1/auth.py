from __future__ import annotations

import uuid
import bcrypt as _bcrypt
import structlog
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, field_validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.core.security import create_access_token
from app.db.session import get_db
from app.models.user import User
from app.core.exceptions import UnauthorizedError

log = structlog.get_logger()
router = APIRouter()


# ── Schemas ───────────────────────────────────────────────────────────────────

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


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserResponse"


class UserResponse(BaseModel):
    id: uuid.UUID
    username: str
    name: str
    avatar_url: str | None
    level: str
    learning_style: str
    goal: str


class UpdateProfileRequest(BaseModel):
    level: str | None = None
    learning_style: str | None = None
    goal: str | None = None
    name: str | None = None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _hash_password(password: str) -> str:
    return _bcrypt.hashpw(password.encode(), _bcrypt.gensalt()).decode()


def _verify_password(plain: str, hashed: str) -> bool:
    return _bcrypt.checkpw(plain.encode(), hashed.encode())


def _user_to_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        username=user.username,
        name=user.name,
        avatar_url=user.avatar_url,
        level=user.level,
        learning_style=user.learning_style,
        goal=user.goal,
    )


# ── Auth routes ───────────────────────────────────────────────────────────────

@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """Create a new account with username & password."""
    result = await db.execute(select(User).where(User.username == body.username))
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="An account with this username already exists")

    user = User(
        username=body.username,
        name=body.username,
        password_hash=_hash_password(body.password),
    )
    db.add(user)
    await db.flush()

    token = create_access_token(str(user.id))
    return TokenResponse(access_token=token, user=_user_to_response(user))


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Sign in with username & password."""
    result = await db.execute(select(User).where(User.username == body.username))
    user = result.scalar_one_or_none()

    if not user or not user.password_hash or not _verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = create_access_token(str(user.id))
    return TokenResponse(access_token=token, user=_user_to_response(user))


@router.get("/me", response_model=UserResponse)
async def get_me(request: Request, db: AsyncSession = Depends(get_db)):
    """Get the currently authenticated user."""
    user = await _get_current_user(request, db)
    return _user_to_response(user)


@router.put("/profile", response_model=UserResponse)
async def update_profile(
    body: UpdateProfileRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user = await _get_current_user(request, db)
    if body.level:
        user.level = body.level
    if body.learning_style:
        user.learning_style = body.learning_style
    if body.goal:
        user.goal = body.goal
    if body.name:
        user.name = body.name
    return _user_to_response(user)


async def _get_current_user(request: Request, db: AsyncSession) -> User:
    """Extract and validate JWT from Authorization header."""
    from jose import JWTError
    from app.core.security import decode_access_token

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise UnauthorizedError("Missing or invalid Authorization header")

    token = auth_header.removeprefix("Bearer ").strip()
    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")
    except JWTError:
        raise UnauthorizedError("Invalid or expired token")

    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user:
        raise UnauthorizedError("User not found")
    return user


# Re-export for dependency injection in other routes
async def get_current_user(
    request: Request, db: AsyncSession = Depends(get_db)
) -> User:
    return await _get_current_user(request, db)
