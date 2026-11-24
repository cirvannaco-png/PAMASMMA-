"""Authenticated JARVIS conversation API."""
from __future__ import annotations

import logging
import time
import uuid
from typing import Annotated, Literal

import httpx

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.config import get_settings
from app.database import get_db
from app.intelligence.engine import CognitiveEngine
from app.jarvis.scope import jarvis_memory_scope
from app.jarvis.service import (
    ConversationNotFound,
    TurnAlreadyInProgress,
    begin_turn,
    conversation_payload,
    create_conversation,
    fail_turn,
    finish_turn,
    get_conversation,
    list_conversations,
)
from app.jarvis.system import JarvisSystem

log = logging.getLogger(__name__)
router = APIRouter(prefix="/jarvis", tags=["JARVIS"])
CurrentUser = Annotated[dict, Depends(get_current_user)]
DbSession = Annotated[AsyncSession | None, Depends(get_db)]


class CreateConversationRequest(BaseModel):
    title: str = Field(default="New conversation", min_length=1, max_length=160)

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Conversation title cannot be blank.")
        return value


class TurnRequest(BaseModel):
    content: str = Field(min_length=1, max_length=12000)
    channel: Literal["text", "voice"] = "text"
    delegation_id: str | None = Field(default=None, min_length=1, max_length=128)

    @field_validator("delegation_id")
    @classmethod
    def validate_delegation_id(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("Delegation ID cannot be blank.")
        return value.strip() if value else None

    @field_validator("content")
    @classmethod
    def normalize_content(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Message content cannot be blank.")
        return value


class VoiceSessionRequest(BaseModel):
    sdp: str = Field(min_length=1, max_length=65536)

    @field_validator("sdp")
    @classmethod
    def normalize_sdp(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("SDP offer cannot be blank.")
        return value


class VoiceDelegationRequest(BaseModel):
    delegation_id: str = Field(min_length=1, max_length=128)
    transcript: str = Field(min_length=1, max_length=12000)

    @field_validator("delegation_id")
    @classmethod
    def normalize_delegation_id(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Delegation ID cannot be blank.")
        return value

    @field_validator("transcript")
    @classmethod
    def normalize_transcript(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Voice transcript cannot be blank.")
        return value


def _require_database(db: AsyncSession | None) -> AsyncSession:
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="JARVIS requires durable PostgreSQL persistence; ephemeral mode is not supported.",
        )
    return db


@router.post("/conversations", status_code=status.HTTP_201_CREATED)
async def create_jarvis_conversation(
    body: CreateConversationRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> dict:
    database = _require_database(db)
    row = await create_conversation(
        database,
        current_user["user_id"],
        body.title,
    )
    return {"conversation": conversation_payload(row)}


@router.get("/conversations")
async def list_jarvis_conversations(
    current_user: CurrentUser,
    db: DbSession,
    limit: int = Query(default=30, ge=1, le=100),
) -> dict:
    database = _require_database(db)
    rows = await list_conversations(
        database,
        current_user["user_id"],
        limit,
    )
    return {
        "conversations": [conversation_payload(row) for row in rows],
        "count": len(rows),
    }


@router.get("/conversations/{conversation_id}")
async def get_jarvis_conversation(
    conversation_id: uuid.UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> dict:
    database = _require_database(db)
    try:
        conversation, messages = await get_conversation(
            database,
            current_user["user_id"],
            conversation_id,
        )
    except ConversationNotFound:
        raise HTTPException(status_code=404, detail="Conversation not found.") from None
    return {
        "conversation": conversation_payload(conversation),
        "messages": [
            {
                "id": str(item.id),
                "sequence": item.sequence,
                "role": item.role,
                "content": item.content,
                "modality": item.modality,
                "created_at": item.created_at.isoformat() if item.created_at else None,
            }
            for item in messages
        ],
    }


@router.post("/conversations/{conversation_id}/voice-sessions")
async def create_jarvis_voice_session(
    conversation_id: uuid.UUID,
    body: VoiceSessionRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> dict:
    database = _require_database(db)
    try:
        _, messages = await get_conversation(
            database,
            current_user["user_id"],
            conversation_id,
        )
    except ConversationNotFound:
        raise HTTPException(status_code=404, detail="Conversation not found.") from None

    settings = get_settings()
    if not settings.openai_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Voice is not configured. Add OPENAI_API_KEY to the PAMASMMA backend secrets.",
        )

    history = []
    for message in messages[-12:]:
        content_type = "input_text" if message.role == "user" else "output_text"
        history.append(
            {
                "type": "message",
                "role": message.role,
                "content": [{"type": content_type, "text": message.content[-900:]}],
            }
        )

    session_payload = {
        "session": {
            "model": "gpt-live-1.1",
            "instructions": (
                "You are JARVIS, the spoken conversation interface for PAMASMMA. "
                "You are not the reasoning or execution authority; PAMASMMA's authenticated "
                "backend CognitiveEngine is. For every substantive question, analysis request, "
                "recommendation, or task, create a client delegation immediately. Do not answer "
                "substantive requests from your own general knowledge. You may respond briefly "
                "to greetings and simple acknowledgements. Never claim an action was completed. "
                "Only PAMASMMA capabilities are in scope. If the backend result is unclear, ask "
                "the user a clarifying question rather than inventing details. Speak calmly, "
                "clearly, naturally, and concisely."
            ),
            "audio": {"output": {"voice": "vesper"}},
            "delegation": {"type": "client"},
            "input": history,
            "store": False,
        },
        "transport": {"type": "webrtc", "sdp": body.sdp},
    }

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
            response = await client.post(
                "https://api.openai.com/v1/live/sessions",
                headers={
                    "Authorization": f"Bearer {settings.openai_api_key}",
                    "Content-Type": "application/json",
                },
                json=session_payload,
            )
    except httpx.HTTPError:
        log.exception("JARVIS Live session transport failed")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not establish the JARVIS voice session.",
        ) from None

    if response.status_code >= 400:
        log.warning(
            "JARVIS Live session rejected",
            extra={"status_code": response.status_code},
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The voice provider rejected the JARVIS session request.",
        )

    try:
        live_result = response.json()
        session_id = live_result["session"]["id"]
        answer_sdp = live_result["transport"]["sdp"]
    except (KeyError, TypeError, ValueError):
        log.exception("JARVIS Live session response was incomplete")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The voice provider returned an incomplete session response.",
        ) from None

    return {
        "session_id": session_id,
        "sdp": answer_sdp,
        "model": "gpt-live-1.1",
        "voice": "vesper",
    }


@router.post("/conversations/{conversation_id}/voice-delegations")
async def complete_jarvis_voice_delegation(
    conversation_id: uuid.UUID,
    body: VoiceDelegationRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> dict:
    result = await submit_jarvis_turn(
        conversation_id,
        TurnRequest(
            content=body.transcript,
            channel="voice",
            delegation_id=body.delegation_id,
        ),
        current_user,
        db,
    )
    return {
        "delegation_id": body.delegation_id,
        "spoken_response": result["assistant_message"]["content"],
        "turn": result,
    }


@router.post("/conversations/{conversation_id}/turns")
async def submit_jarvis_turn(
    conversation_id: uuid.UUID,
    body: TurnRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> dict:
    database = _require_database(db)
    user_id = current_user["user_id"]
    try:
        turn_id, history, user_message = await begin_turn(
            database,
            user_id,
            conversation_id,
            body.content,
            modality=body.channel,
            delegation_id=body.delegation_id,
        )
    except ConversationNotFound:
        raise HTTPException(status_code=404, detail="Conversation not found.") from None
    except TurnAlreadyInProgress:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="JARVIS is already processing a turn in this conversation.",
        ) from None

    scope_id = jarvis_memory_scope(user_id)
    system = JarvisSystem(memory_scope_id=scope_id, channel=body.channel)
    started = time.perf_counter()
    try:
        result = await CognitiveEngine().run(
            system,
            history,
            user_id,
            memory_scope_id=scope_id,
        )
        trace = result.trace.model_dump(mode="json")
        await system._post_invoke(
            user_id=user_id,
            query=body.content,
            response=result.response,
            latency_ms=(time.perf_counter() - started) * 1000,
            trace=trace,
        )
        assistant_message = await finish_turn(
            database,
            user_id,
            conversation_id,
            turn_id,
            result.response,
            modality=body.channel,
        )
        if assistant_message is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="The conversation turn lease expired or was replaced; the response was not committed.",
            )
    except HTTPException:
        await fail_turn(database, user_id, conversation_id, turn_id)
        raise
    except Exception:
        await fail_turn(database, user_id, conversation_id, turn_id)
        log.exception("JARVIS turn failed", extra={"user_id": user_id, "conversation_id": str(conversation_id)})
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="JARVIS could not complete this turn. Your message is saved; you can retry.",
        ) from None

    return {
        "conversation_id": str(conversation_id),
        "turn_id": str(turn_id),
        "user_message": user_message,
        "assistant_message": assistant_message,
        "cognition": trace,
        "decision": result.decision.model_dump(mode="json"),
    }
