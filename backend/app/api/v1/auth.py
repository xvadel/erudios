from __future__ import annotations

import uuid
from typing import Annotated

import httpx
import structlog
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.core.security import create_access_token
from app.db.session import get_db
from app.models.user import User
from app.core.exceptions import UnauthorizedError

log = structlog.get_logger()
router = APIRouter()

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

GITHUB_AUTH_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USERINFO_URL = "https://api.github.com/user"
GITHUB_EMAILS_URL = "https://api.github.com/user/emails"


# ── Schemas ───────────────────────────────────────────────────────────────────

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserResponse"


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
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

def _callback_url(provider: str) -> str:
    return f"{settings.OAUTH_REDIRECT_BASE_URL}/api/v1/auth/callback/{provider}"


async def _get_or_create_user(
    db: AsyncSession,
    email: str,
    name: str,
    avatar_url: str | None,
    oauth_provider: str,
    oauth_id: str,
) -> User:
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user:
        # Update OAuth info if changed
        user.oauth_provider = oauth_provider
        user.oauth_id = oauth_id
        if avatar_url:
            user.avatar_url = avatar_url
        return user

    user = User(
        email=email,
        name=name,
        avatar_url=avatar_url,
        oauth_provider=oauth_provider,
        oauth_id=str(oauth_id),
    )
    db.add(user)
    await db.flush()
    return user


def _user_to_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        avatar_url=user.avatar_url,
        level=user.level,
        learning_style=user.learning_style,
        goal=user.goal,
    )


# ── OAuth routes ──────────────────────────────────────────────────────────────

@router.get("/google")
async def google_login():
    if not settings.has_google_oauth:
        raise HTTPException(status_code=503, detail="Google OAuth not configured")
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": _callback_url("google"),
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
    }
    url = GOOGLE_AUTH_URL + "?" + "&".join(f"{k}={v}" for k, v in params.items())
    return RedirectResponse(url)


@router.get("/github")
async def github_login():
    if not settings.has_github_oauth:
        raise HTTPException(status_code=503, detail="GitHub OAuth not configured")
    params = {
        "client_id": settings.GITHUB_CLIENT_ID,
        "redirect_uri": _callback_url("github"),
        "scope": "user:email",
    }
    url = GITHUB_AUTH_URL + "?" + "&".join(f"{k}={v}" for k, v in params.items())
    return RedirectResponse(url)


@router.get("/callback/google", response_model=TokenResponse)
async def google_callback(code: str, db: AsyncSession = Depends(get_db)):
    async with httpx.AsyncClient() as client:
        # Exchange code for token
        token_resp = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": _callback_url("google"),
                "grant_type": "authorization_code",
            },
        )
        token_resp.raise_for_status()
        tokens = token_resp.json()

        # Get user info
        user_resp = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        user_resp.raise_for_status()
        info = user_resp.json()

    user = await _get_or_create_user(
        db,
        email=info["email"],
        name=info.get("name", ""),
        avatar_url=info.get("picture"),
        oauth_provider="google",
        oauth_id=info["id"],
    )
    token = create_access_token(str(user.id))
    return TokenResponse(access_token=token, user=_user_to_response(user))


@router.get("/callback/github", response_model=TokenResponse)
async def github_callback(code: str, db: AsyncSession = Depends(get_db)):
    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            GITHUB_TOKEN_URL,
            headers={"Accept": "application/json"},
            data={
                "client_id": settings.GITHUB_CLIENT_ID,
                "client_secret": settings.GITHUB_CLIENT_SECRET,
                "code": code,
                "redirect_uri": _callback_url("github"),
            },
        )
        token_resp.raise_for_status()
        tokens = token_resp.json()
        access_token = tokens.get("access_token")
        if not access_token:
            raise HTTPException(status_code=400, detail="GitHub OAuth failed")

        headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}
        user_resp = await client.get(GITHUB_USERINFO_URL, headers=headers)
        user_resp.raise_for_status()
        info = user_resp.json()

        # GitHub may not expose email — fetch from emails endpoint
        email = info.get("email")
        if not email:
            emails_resp = await client.get(GITHUB_EMAILS_URL, headers=headers)
            emails_resp.raise_for_status()
            for e in emails_resp.json():
                if e.get("primary") and e.get("verified"):
                    email = e["email"]
                    break

    if not email:
        raise HTTPException(status_code=400, detail="Could not retrieve email from GitHub")

    user = await _get_or_create_user(
        db,
        email=email,
        name=info.get("name") or info.get("login", ""),
        avatar_url=info.get("avatar_url"),
        oauth_provider="github",
        oauth_id=str(info["id"]),
    )
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
