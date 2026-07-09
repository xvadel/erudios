from __future__ import annotations

import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.api.v1.auth import get_current_user
from app.models.user import User
from app.modules.rag.service import rag_service
from app.modules.rag.indexer import rag_indexer
from app.schemas.chat import (
    ChatSessionCreate, ChatSessionOut, ChatMessageCreate, ChatMessageOut
)

router = APIRouter()


# ── Helper ────────────────────────────────────────────────────────────────────

def _session_to_out(session, message_count: int = 0) -> ChatSessionOut:
    return ChatSessionOut(
        id=session.id,
        topic_slug=session.topic.slug,
        topic_name=session.topic.name,
        message_count=message_count,
        created_at=session.created_at,
    )


def _message_to_out(msg) -> ChatMessageOut:
    return ChatMessageOut(
        id=msg.id,
        session_id=msg.session_id,
        role=msg.role,
        content=msg.content,
        sources=msg.sources or [],
        tokens_used=msg.tokens_used,
        created_at=msg.created_at,
    )


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/sessions", response_model=ChatSessionOut, status_code=201)
async def create_chat_session(
    body: ChatSessionCreate,
    background_tasks: BackgroundTasks,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new chat session for a topic.
    Triggers resource indexing in the background (idempotent — safe to call multiple times).
    """
    user: User = await get_current_user(request, db)
    session = await rag_service.create_session(db, user.id, body.topic_slug)

    # Ensure topic resources are indexed in Qdrant (runs in background, non-blocking)
    background_tasks.add_task(_index_topic_background, body.topic_slug)

    return _session_to_out(session, message_count=0)


@router.get("/sessions", response_model=list[ChatSessionOut])
async def list_chat_sessions(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """List all chat sessions for the authenticated user."""
    user: User = await get_current_user(request, db)
    sessions = await rag_service.list_sessions(db, user.id)
    return [_session_to_out(s, len(s.messages) if hasattr(s, "messages") else 0) for s in sessions]


@router.get("/sessions/{session_id}", response_model=ChatSessionOut)
async def get_chat_session(
    session_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Get a chat session with its message history."""
    user: User = await get_current_user(request, db)
    session = await rag_service.get_session(db, session_id, user.id)
    return _session_to_out(session, len(session.messages))


@router.get("/sessions/{session_id}/messages", response_model=list[ChatMessageOut])
async def get_chat_messages(
    session_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Get all messages in a chat session, ordered chronologically."""
    user: User = await get_current_user(request, db)
    messages = await rag_service.get_messages(db, session_id, user.id)
    return [_message_to_out(m) for m in messages]


@router.post("/sessions/{session_id}/messages")
async def send_message(
    session_id: uuid.UUID,
    body: ChatMessageCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Send a message in a chat session.
    Returns a Server-Sent Events (SSE) stream.

    The frontend should consume this as an EventSource or fetch with streaming.
    Each SSE event contains a text token chunk.
    Final event: `data: [DONE]` signals completion.
    """
    user: User = await get_current_user(request, db)

    async def event_generator():
        async for chunk in rag_service.chat_stream(
            db=db,
            session_id=session_id,
            user_id=user.id,
            user_message=body.content,
        ):
            yield chunk

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # Disable Nginx buffering
        },
    )


@router.post("/topics/{topic_slug}/index", status_code=202)
async def index_topic_resources(
    topic_slug: str,
    background_tasks: BackgroundTasks,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Manually trigger Qdrant indexing for a topic's resources.
    Returns 202 Accepted immediately — indexing runs in background.
    """
    await get_current_user(request, db)  # Auth required
    background_tasks.add_task(_index_topic_background, topic_slug)
    return {"message": f"Indexing started for topic '{topic_slug}'", "status": "accepted"}


# ── Background helpers ────────────────────────────────────────────────────────

async def _index_topic_background(topic_slug: str) -> None:
    """Background task: index topic resources into Qdrant."""
    from app.db.session import AsyncSessionLocal
    import structlog
    log = structlog.get_logger()
    async with AsyncSessionLocal() as db:
        try:
            count = await rag_indexer.index_topic(db, topic_slug)
            log.info("Background RAG indexing complete", topic=topic_slug, count=count)
        except Exception as exc:
            log.error("Background RAG indexing failed", topic=topic_slug, error=str(exc))
