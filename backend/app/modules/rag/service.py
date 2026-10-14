from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import AsyncIterator

import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.chat import ChatSession, ChatMessage
from app.models.topic import Topic
from app.providers.embeddings import get_embedding_provider, qdrant_store
from app.providers.embeddings.qdrant_store import SearchResult
from app.providers.llms.router import provider_router
from app.providers.llms.budget import TaskType
from app.core.exceptions import NotFoundError

log = structlog.get_logger()

# How many resource chunks to retrieve per query
_RETRIEVAL_K = 5

_SYSTEM_PROMPT = """\
You are an expert AI/ML tutor for the Erudios learning platform.
You have access to curated learning resources for this topic.
Answer the student's question clearly and accurately.
When you reference a resource, cite it using [Source N] notation.
Keep your answer focused, structured with markdown, and educational.
"""


class RAGService:
    """
    Retrieval-Augmented Generation chat service.

    Flow for each user message:
    1. Embed the user query
    2. Retrieve top-K relevant resource chunks from Qdrant (filtered by topic)
    3. Build a context prompt with the retrieved chunks
    4. Stream the LLM response token-by-token via SSE
    5. Persist the complete response as a ChatMessage row
    """

    # ── Session management ────────────────────────────────────────────────────

    async def get_or_create_session(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        topic_slug: str,
    ) -> ChatSession:
        """Return the most recent session for this user+topic, or create one."""
        topic_result = await db.execute(
            select(Topic).where(Topic.slug == topic_slug)
        )
        topic = topic_result.scalar_one_or_none()
        if not topic:
            raise NotFoundError(f"Topic '{topic_slug}' not found")

        result = await db.execute(
            select(ChatSession)
            .where(ChatSession.user_id == user_id, ChatSession.topic_id == topic.id)
            .order_by(ChatSession.created_at.desc())
            .limit(1)
        )
        session = result.scalar_one_or_none()
        if not session:
            session = ChatSession(user_id=user_id, topic_id=topic.id)
            db.add(session)
            await db.flush()

        return session

    async def create_session(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        topic_slug: str,
    ) -> ChatSession:
        """Always create a fresh chat session for a topic."""
        topic_result = await db.execute(
            select(Topic).where(Topic.slug == topic_slug)
        )
        topic = topic_result.scalar_one_or_none()
        if not topic:
            raise NotFoundError(f"Topic '{topic_slug}' not found")

        session = ChatSession(user_id=user_id, topic_id=topic.id)
        db.add(session)
        await db.flush()
        return session

    async def get_session(
        self, db: AsyncSession, session_id: uuid.UUID, user_id: uuid.UUID
    ) -> ChatSession:
        result = await db.execute(
            select(ChatSession)
            .where(ChatSession.id == session_id, ChatSession.user_id == user_id)
            .options(selectinload(ChatSession.messages), selectinload(ChatSession.topic))
        )
        session = result.scalar_one_or_none()
        if not session:
            raise NotFoundError("Chat session not found")
        return session

    async def list_sessions(
        self, db: AsyncSession, user_id: uuid.UUID
    ) -> list[ChatSession]:
        result = await db.execute(
            select(ChatSession)
            .where(ChatSession.user_id == user_id)
            .options(selectinload(ChatSession.topic))
            .order_by(ChatSession.created_at.desc())
        )
        return list(result.scalars().all())

    # ── Message history ───────────────────────────────────────────────────────

    async def get_messages(
        self, db: AsyncSession, session_id: uuid.UUID, user_id: uuid.UUID
    ) -> list[ChatMessage]:
        """Get all messages for a session (verifies ownership)."""
        session = await self.get_session(db, session_id, user_id)
        result = await db.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session.id)
            .order_by(ChatMessage.created_at.asc())
        )
        return list(result.scalars().all())

    # ── Core: RAG streaming chat ──────────────────────────────────────────────

    async def chat_stream(
        self,
        db: AsyncSession,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
        user_message: str,
    ) -> AsyncIterator[str]:
        """
        SSE generator that:
        1. Saves the user message
        2. Retrieves relevant chunks from Qdrant
        3. Streams LLM response tokens
        4. Saves the complete assistant message on completion

        Yields SSE-formatted strings: "data: <token>\n\n"
        Final event: "data: [DONE]\n\n"
        """
        session = await self.get_session(db, session_id, user_id)
        topic_slug = session.topic.slug

        # 1. Save user message
        user_msg = ChatMessage(
            session_id=session_id,
            role="user",
            content=user_message,
            sources=[],
            tokens_used=0,
        )
        db.add(user_msg)
        await db.flush()

        # 2. Retrieve context from Qdrant
        sources: list[dict] = []
        context_block = ""
        try:
            embedding_provider = get_embedding_provider()
            query_vector = await embedding_provider.embed_one(user_message)
            hits: list[SearchResult] = await qdrant_store.search(
                query_vector=query_vector,
                limit=_RETRIEVAL_K,
                topic_slug=topic_slug,
            )
            if hits:
                context_lines = []
                for i, hit in enumerate(hits, start=1):
                    sources.append({
                        "index": i,
                        "title": hit.title,
                        "url": hit.url,
                        "score": round(hit.score, 3),
                        "source_type": hit.payload.get("source_type", ""),
                    })
                    context_lines.append(
                        f"[Source {i}] {hit.title}\n{hit.text[:400]}"
                    )
                context_block = "Relevant resources:\n\n" + "\n\n".join(context_lines)
        except Exception as exc:
            log.warning("RAG retrieval failed, proceeding without context", error=str(exc))

        # 3. Build conversation history (last 10 messages for context window)
        history_result = await db.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.asc())
            .limit(20)
        )
        history = list(history_result.scalars().all())

        history_text = "\n".join(
            f"{'Student' if m.role == 'user' else 'Tutor'}: {m.content}"
            for m in history[:-1]  # Exclude the message we just saved
        )

        prompt = f"""\
{f'Conversation so far:{chr(10)}{history_text}{chr(10)}' if history_text else ''}\
{f'{chr(10)}{context_block}{chr(10)}' if context_block else ''}\
Student: {user_message}

Tutor:"""

        # 4. Stream LLM response
        full_response = ""
        total_tokens = 0

        try:
            # Use non-streaming route for now — yields full response
            # TODO: Switch to true token streaming when providers support it
            response = await provider_router.route(
                task=TaskType.REASONING,
                prompt=prompt,
                system_prompt=_SYSTEM_PROMPT,
                temperature=0.5,
                max_tokens=1024,
            )
            total_tokens = response.total_tokens

            # Simulate streaming by chunking the response into sentences
            full_response = response.content
            words = full_response.split(" ")
            chunk_size = 4
            for i in range(0, len(words), chunk_size):
                chunk = " ".join(words[i:i + chunk_size])
                if i + chunk_size < len(words):
                    chunk += " "
                yield f"data: {chunk}\n\n"

        except Exception as exc:
            error_msg = "I'm sorry, I encountered an error generating a response. Please try again."
            full_response = error_msg
            log.error("RAG LLM generation failed", session_id=session_id, error=str(exc))
            yield f"data: {error_msg}\n\n"

        # 5. Save complete assistant message
        assistant_msg = ChatMessage(
            session_id=session_id,
            role="assistant",
            content=full_response,
            sources=sources,
            tokens_used=total_tokens,
        )
        db.add(assistant_msg)
        await db.flush()

        yield "data: [DONE]\n\n"


rag_service = RAGService()
