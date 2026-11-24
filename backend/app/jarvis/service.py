"""Persistence operations for authenticated JARVIS conversations."""
from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import desc, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.jarvis import (
    JarvisConversation,
    JarvisMessage,
    JarvisVoiceDelegation,
    JarvisVoiceSession,
    JarvisVoiceUsage,
)


class ConversationNotFound(Exception):
    pass


class TurnAlreadyInProgress(Exception):
    pass


class DelegationAlreadyInProgress(Exception):
    pass


class DelegationConflict(Exception):
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

    user_message = None
    if delegation_id is not None:
        existing_message_result = await db.execute(
            select(JarvisMessage).where(
                JarvisMessage.conversation_id == conversation_id,
                JarvisMessage.user_id == user_id,
                JarvisMessage.metadata_["delegation_id"].as_string() == delegation_id,
            ).order_by(JarvisMessage.sequence.asc()).limit(1).with_for_update()
        )
        user_message = existing_message_result.scalar_one_or_none()
    if user_message is not None:
        user_message.metadata_ = {**(user_message.metadata_ or {}), "turn_id": str(turn_id)}
    else:
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


async def register_voice_session(
    db: AsyncSession,
    user_id: str,
    conversation_id: uuid.UUID,
    provider_session_id: str,
    model: str,
) -> JarvisVoiceSession:
    row = JarvisVoiceSession(
        user_id=user_id,
        conversation_id=conversation_id,
        provider_session_id=provider_session_id,
        model=model,
        status="active",
        expires_at=datetime.now(UTC) + timedelta(hours=1),
    )
    db.add(row)
    await db.flush()
    db.add(JarvisVoiceUsage(
        voice_session_id=row.id,
        user_id=user_id,
        model=model,
        status="awaiting_provider",
    ))
    await db.commit()
    await db.refresh(row)
    return row


async def close_voice_session(
    db: AsyncSession,
    user_id: str,
    conversation_id: uuid.UUID,
    provider_session_id: str,
) -> bool:
    result = await db.execute(
        select(JarvisVoiceSession).where(
            JarvisVoiceSession.provider_session_id == provider_session_id,
            JarvisVoiceSession.user_id == user_id,
            JarvisVoiceSession.conversation_id == conversation_id,
        ).with_for_update()
    )
    row = result.scalar_one_or_none()
    if row is None:
        return False
    if row.status == "active":
        row.status = "closed"
        row.closed_at = datetime.now(UTC)
        await db.commit()
    return True


async def claim_voice_delegation(
    db: AsyncSession,
    user_id: str,
    conversation_id: uuid.UUID,
    delegation_id: str,
    transcript: str,
) -> tuple[str, dict | None]:
    """Durably claim an idempotency key before any cognitive work is started."""
    digest = hashlib.sha256(transcript.encode("utf-8")).hexdigest()
    existing_result = await db.execute(
        select(JarvisVoiceDelegation).where(
            JarvisVoiceDelegation.user_id == user_id,
            JarvisVoiceDelegation.conversation_id == conversation_id,
            JarvisVoiceDelegation.delegation_id == delegation_id,
        ).with_for_update()
    )
    existing = existing_result.scalar_one_or_none()
    if existing is not None:
        if existing.transcript_sha256 != digest:
            raise DelegationConflict
        if existing.status == "completed" and existing.response_payload is not None:
            return "completed", existing.response_payload
        if existing.status == "processing":
            if existing.updated_at is None or existing.updated_at > datetime.now(UTC) - timedelta(minutes=5):
                raise DelegationAlreadyInProgress
            existing.status = "failed"
        session_result = await db.execute(
            select(JarvisVoiceSession.provider_session_id)
            .where(
                JarvisVoiceSession.user_id == user_id,
                JarvisVoiceSession.conversation_id == conversation_id,
                JarvisVoiceSession.status == "active",
                (JarvisVoiceSession.expires_at.is_(None) | (JarvisVoiceSession.expires_at > datetime.now(UTC))),
            )
            .order_by(desc(JarvisVoiceSession.created_at))
            .limit(1)
        )
        provider_session_id = session_result.scalar_one_or_none()
        if provider_session_id is None:
            raise ConversationNotFound
        existing.status = "processing"
        existing.response_payload = None
        existing.provider_session_id = provider_session_id
        existing.updated_at = datetime.now(UTC)
        await db.commit()
        return "claimed", None

    session_result = await db.execute(
        select(JarvisVoiceSession.provider_session_id)
        .where(
            JarvisVoiceSession.user_id == user_id,
            JarvisVoiceSession.conversation_id == conversation_id,
            JarvisVoiceSession.status == "active",
            (JarvisVoiceSession.expires_at.is_(None) | (JarvisVoiceSession.expires_at > datetime.now(UTC))),
        )
        .order_by(desc(JarvisVoiceSession.created_at))
        .limit(1)
    )
    provider_session_id = session_result.scalar_one_or_none()
    if provider_session_id is None:
        raise ConversationNotFound

    row = JarvisVoiceDelegation(
        user_id=user_id,
        conversation_id=conversation_id,
        provider_session_id=provider_session_id,
        delegation_id=delegation_id,
        transcript_sha256=digest,
        status="processing",
    )
    db.add(row)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raced_result = await db.execute(
            select(JarvisVoiceDelegation).where(
                JarvisVoiceDelegation.user_id == user_id,
                JarvisVoiceDelegation.conversation_id == conversation_id,
                JarvisVoiceDelegation.delegation_id == delegation_id,
            )
        )
        raced = raced_result.scalar_one_or_none()
        if raced is None or raced.transcript_sha256 != digest:
            raise DelegationConflict from None
        if raced.status == "completed" and raced.response_payload is not None:
            return "completed", raced.response_payload
        raise DelegationAlreadyInProgress from None
    return "claimed", None


async def finish_voice_delegation(
    db: AsyncSession,
    user_id: str,
    conversation_id: uuid.UUID,
    delegation_id: str,
    response_payload: dict | None = None,
) -> None:
    result = await db.execute(
        select(JarvisVoiceDelegation).where(
            JarvisVoiceDelegation.user_id == user_id,
            JarvisVoiceDelegation.conversation_id == conversation_id,
            JarvisVoiceDelegation.delegation_id == delegation_id,
        ).with_for_update()
    )
    row = result.scalar_one_or_none()
    if row is None:
        return
    row.status = "completed" if response_payload is not None else "failed"
    row.response_payload = response_payload
    row.updated_at = datetime.now(UTC)
    await db.commit()


async def finish_turn_with_voice_delegation(
    db: AsyncSession,
    user_id: str,
    conversation_id: uuid.UUID,
    turn_id: uuid.UUID,
    response: str,
    delegation_id: str,
    user_message: dict,
    cognition: dict,
    decision: dict,
) -> tuple[dict, dict] | None:
    """Commit the assistant message and idempotent response cache atomically."""
    result = await db.execute(
        select(JarvisConversation).where(
            JarvisConversation.id == conversation_id,
            JarvisConversation.user_id == user_id,
        ).with_for_update()
    )
    conversation = result.scalar_one_or_none()
    if conversation is None or conversation.active_turn_id != turn_id:
        return None
    delegation_result = await db.execute(
        select(JarvisVoiceDelegation).where(
            JarvisVoiceDelegation.user_id == user_id,
            JarvisVoiceDelegation.conversation_id == conversation_id,
            JarvisVoiceDelegation.delegation_id == delegation_id,
        ).with_for_update()
    )
    delegation = delegation_result.scalar_one_or_none()
    if delegation is None or delegation.status != "processing":
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
        modality="voice",
        metadata_={"turn_id": str(turn_id), "delegation_id": delegation_id},
    )
    db.add(assistant_message)
    conversation.active_turn_id = None
    conversation.active_turn_expires_at = None
    conversation.last_message_at = now
    conversation.updated_at = now
    await db.flush()
    assistant_payload = message_payload(assistant_message)
    response_payload = {
        "conversation_id": str(conversation_id),
        "turn_id": str(turn_id),
        "user_message": user_message,
        "assistant_message": assistant_payload,
        "cognition": cognition,
        "decision": decision,
    }
    delegation.status = "completed"
    delegation.response_payload = response_payload
    delegation.updated_at = now
    await db.commit()
    return assistant_payload, response_payload
