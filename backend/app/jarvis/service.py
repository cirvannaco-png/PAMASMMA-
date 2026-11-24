"""Persistence operations for authenticated JARVIS conversations."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.jarvis import JarvisConversation, JarvisMessage


class ConversationNotFound(Exception):
    pass


class TurnAlreadyInProgress(Exception):
    pass


def conversation_payload(row: JarvisConversation) -> dict:
    return {
        "id": str(row.id),
        "title": row.title,
        "status": row.status,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        "last_message_at": row.last_message_at.isoformat() if row.last_message_at else None,
    }


def message_payload(row: JarvisMessage) -> dict:
    return {
        "id": str(row.id),
        "sequence": row.sequence,
        "role": row.role,
        "content": row.content,
        "modality": row.modality,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


async def create_conversation(
    db: AsyncSession,
    user_id: str,
    title: str,
) -> JarvisConversation:
    row = JarvisConversation(user_id=user_id, title=title[:160])
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


async def list_conversations(
    db: AsyncSession,
    user_id: str,
    limit: int,
) -> list[JarvisConversation]:
    result = await db.execute(
        select(JarvisConversation)
        .where(
            JarvisConversation.user_id == user_id,
            JarvisConversation.status == "active",
        )
        .order_by(desc(JarvisConversation.updated_at))
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_conversation(
    db: AsyncSession,
    user_id: str,
    conversation_id: uuid.UUID,
) -> tuple[JarvisConversation, list[JarvisMessage]]:
    result = await db.execute(
        select(JarvisConversation).where(
            JarvisConversation.id == conversation_id,
            JarvisConversation.user_id == user_id,
        )
    )
    conversation = result.scalar_one_or_none()
    if conversation is None:
        raise ConversationNotFound

    messages_result = await db.execute(
        select(JarvisMessage)
        .where(
            JarvisMessage.conversation_id == conversation_id,
            JarvisMessage.user_id == user_id,
        )
        .order_by(JarvisMessage.sequence.asc())
        .limit(500)
    )
    return conversation, list(messages_result.scalars().all())


async def begin_turn(
    db: AsyncSession,
    user_id: str,
    conversation_id: uuid.UUID,
    content: str,
    modality: str = "text",
    delegation_id: str | None = None,
) -> tuple[uuid.UUID, list[dict], dict]:
    """Acquire a database-backed conversation lease and persist the user turn."""
    result = await db.execute(
        select(JarvisConversation)
        .where(
            JarvisConversation.id == conversation_id,
            JarvisConversation.user_id == user_id,
            JarvisConversation.status == "active",
        )
        .with_for_update()
    )
    conversation = result.scalar_one_or_none()
    if conversation is None:
        raise ConversationNotFound

    now = datetime.now(UTC)
    if conversation.active_turn_id is not None and (
        conversation.active_turn_expires_at is None
        or conversation.active_turn_expires_at > now
    ):
        raise TurnAlreadyInProgress

    if conversation.title == "New conversation":
        conversation.title = " ".join(content.split())[:80] or "New conversation"

    turn_id = uuid.uuid4()
    conversation.active_turn_id = turn_id
    conversation.active_turn_expires_at = now + timedelta(minutes=5)

    current_sequence = await db.scalar(
        select(func.coalesce(func.max(JarvisMessage.sequence), 0)).where(
            JarvisMessage.conversation_id == conversation_id
        )
    )
    user_message = JarvisMessage(
        conversation_id=conversation_id,
        user_id=user_id,
        sequence=int(current_sequence or 0) + 1,
        role="user",
        content=content,
        modality=modality,
        metadata_={
            "turn_id": str(turn_id),
            "delegation_id": delegation_id,
        },
    )
    db.add(user_message)
    conversation.last_message_at = now
    conversation.updated_at = now
    await db.commit()
    await db.refresh(user_message)

    history_result = await db.execute(
        select(JarvisMessage)
        .where(
            JarvisMessage.conversation_id == conversation_id,
            JarvisMessage.user_id == user_id,
        )
        .order_by(desc(JarvisMessage.sequence))
        .limit(15)
    )
    history_rows = list(reversed(history_result.scalars().all()))
    history = [{"role": item.role, "content": item.content} for item in history_rows]
    return turn_id, history, message_payload(user_message)


async def finish_turn(
    db: AsyncSession,
    user_id: str,
    conversation_id: uuid.UUID,
    turn_id: uuid.UUID,
    response: str,
    modality: str = "text",
) -> dict | None:
    result = await db.execute(
        select(JarvisConversation)
        .where(
            JarvisConversation.id == conversation_id,
            JarvisConversation.user_id == user_id,
        )
        .with_for_update()
    )
    conversation = result.scalar_one_or_none()
    if conversation is None or conversation.active_turn_id != turn_id:
        return None

    current_sequence = await db.scalar(
        select(func.coalesce(func.max(JarvisMessage.sequence), 0)).where(
            JarvisMessage.conversation_id == conversation_id
        )
    )
    now = datetime.now(UTC)
    assistant_message = JarvisMessage(
        conversation_id=conversation_id,
        user_id=user_id,
        sequence=int(current_sequence or 0) + 1,
        role="assistant",
        content=response,
        modality=modality,
        metadata_={"turn_id": str(turn_id)},
    )
    db.add(assistant_message)
    conversation.active_turn_id = None
    conversation.active_turn_expires_at = None
    conversation.last_message_at = now
    conversation.updated_at = now
    await db.commit()
    await db.refresh(assistant_message)
    return message_payload(assistant_message)


async def fail_turn(
    db: AsyncSession,
    user_id: str,
    conversation_id: uuid.UUID,
    turn_id: uuid.UUID,
) -> None:
    result = await db.execute(
        select(JarvisConversation)
        .where(
            JarvisConversation.id == conversation_id,
            JarvisConversation.user_id == user_id,
        )
        .with_for_update()
    )
    conversation = result.scalar_one_or_none()
    if conversation is not None and conversation.active_turn_id == turn_id:
        conversation.active_turn_id = None
        conversation.active_turn_expires_at = None
        await db.commit()
