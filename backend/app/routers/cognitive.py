"""
PAMASMMA v4.2 — Cognitive Router.
"""
import json
import time
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.auth.dependencies import get_current_user
from app.database import pg_event_bus
from app.intelligence.contracts import FailureDomain, OutcomeRecord
from app.intelligence.learning import (
    OutcomeLearningEngine,
    estimate_prediction_error,
    infer_failure_domain,
)
from app.intelligence.persistence import (
    create_outcome,
    get_decision,
    list_decisions,
    list_outcomes,
)
from app.services.action_log import list_action_log
from app.systems import SYSTEM_METADATA, get_system

router = APIRouter(prefix="/cognitive", tags=["Cognitive Systems"])
CurrentUser = Annotated[dict, Depends(get_current_user)]


class Message(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str = Field(..., min_length=1, max_length=32000)


class InvokeRequest(BaseModel):
    system_id: str = Field(..., pattern="^S([1-9]|10)$")
    messages: list[Message] = Field(..., min_length=1, max_length=50)
    stream: bool = False


class OverrideRequest(BaseModel):
    system_id: str = Field(..., pattern="^S([1-9]|10)$")
    directive: str = Field(..., min_length=10, max_length=2000)
    reason: str = Field(..., min_length=5, max_length=500)


class OutcomeRequest(BaseModel):
    observed_outcome: str = Field(
        ...,
        min_length=2,
        max_length=10000,
    )
    success_score: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )
    failure_domain: FailureDomain = FailureDomain.UNKNOWN
    lesson: str = Field(
        default="",
        max_length=3000,
    )


@router.get("/systems")
async def list_systems(_: CurrentUser) -> dict:
    return {
        "systems": SYSTEM_METADATA,
        "count": len(SYSTEM_METADATA),
    }


@router.post("/invoke", response_model=None)
async def invoke_system(
    body: InvokeRequest,
    current_user: CurrentUser,
) -> dict | StreamingResponse:
    try:
        system = get_system(body.system_id)
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"System {body.system_id} not found.",
        ) from None

    messages = [
        {
            "role": message.role,
            "content": message.content,
        }
        for message in body.messages
    ]
    user_id = current_user["user_id"]

    if body.stream:
        async def event_stream():
            generator = await system.invoke(
                messages,
                user_id,
                stream=True,
            )
            async for chunk in generator:
                yield (
                    "data: "
                    + json.dumps(chunk)
                    + "\n\n"
                )
            yield "data: [DONE]\n\n"

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache, no-transform",
                "X-Accel-Buffering": "no",
            },
        )

    start = time.perf_counter()
    from app.intelligence.engine import CognitiveEngine

    result = await CognitiveEngine().run(
        system,
        messages,
        user_id,
    )
    await system._post_invoke(
        user_id=user_id,
        query=next(
            (
                message["content"]
                for message in reversed(messages)
                if message["role"] == "user"
            ),
            "",
        ),
        response=result.response,
        latency_ms=(time.perf_counter() - start) * 1000,
        trace=result.trace.model_dump(mode="json"),
    )

    return {
        "system_id": body.system_id,
        "system_name": system.system_name,
        "response": result.response,
        "cognition": result.trace.model_dump(mode="json"),
        "decision": result.decision.model_dump(mode="json"),
    }


@router.get("/decisions")
async def get_decisions(
    current_user: CurrentUser,
    limit: int = Query(default=50, ge=1, le=200),
) -> dict:
    entries = await list_decisions(
        current_user["user_id"],
        limit,
    )
    return {
        "entries": entries,
        "count": len(entries),
    }


@router.get("/decisions/{decision_id}")
async def get_decision_detail(
    decision_id: str,
    current_user: CurrentUser,
) -> dict:
    record = await get_decision(
        decision_id,
        current_user["user_id"],
    )
    if not record:
        raise HTTPException(
            status_code=404,
            detail="Decision not found.",
        )
    return record


@router.post("/decisions/{decision_id}/outcome")
async def record_decision_outcome(
    decision_id: str,
    body: OutcomeRequest,
    current_user: CurrentUser,
) -> dict:
    decision = await get_decision(
        decision_id,
        current_user["user_id"],
    )
    if not decision:
        raise HTTPException(
            status_code=404,
            detail="Decision not found.",
        )

    confidence = float(
        decision.get("confidence", 0.5)
    )
    failure_domain = body.failure_domain
    if failure_domain == FailureDomain.UNKNOWN:
        failure_domain = infer_failure_domain(
            body.observed_outcome
        )

    outcome_id = str(uuid.uuid4())
    outcome = OutcomeRecord(
        id=outcome_id,
        decision_id=decision_id,
        user_id=current_user["user_id"],
        expected_outcome=decision.get(
            "expected_outcome"
        ) or "",
        observed_outcome=body.observed_outcome,
        success_score=body.success_score,
        prediction_error=estimate_prediction_error(
            body.success_score,
            confidence,
        ),
        failure_domain=failure_domain,
        lesson=body.lesson,
        metadata={
            "calibration_delta": (
                body.success_score - confidence
                if body.success_score is not None
                else None
            ),
        },
    )
    lesson = await OutcomeLearningEngine().learn(
        outcome
    )
    outcome = outcome.model_copy(
        update={"lesson": lesson}
    )
    outcome_id = await create_outcome(
        outcome.model_dump(mode="json")
    )

    await pg_event_bus.publish(
        channel="cognitive_outcome",
        payload={
            "user_id": current_user["user_id"],
            "decision_id": decision_id,
            "outcome_id": outcome_id,
            "success_score": body.success_score,
            "prediction_error": outcome.prediction_error,
            "failure_domain": failure_domain.value,
        },
    )

    return {
        "status": "learned",
        "outcome": outcome.model_dump(
            mode="json"
        ),
    }


@router.get("/outcomes")
async def get_outcomes(
    current_user: CurrentUser,
    limit: int = Query(default=50, ge=1, le=200),
) -> dict:
    entries = await list_outcomes(
        current_user["user_id"],
        limit,
    )
    return {
        "entries": entries,
        "count": len(entries),
    }


@router.get("/action-log")
async def get_action_log(
    current_user: CurrentUser,
    limit: int = Query(default=50, ge=1, le=200),
    system_id: str | None = Query(
        default=None,
        pattern="^S([1-9]|10)$",
    ),
) -> dict:
    entries = await list_action_log(
        user_id=current_user["user_id"],
        limit=limit,
        system_id=system_id,
    )
    return {
        "entries": entries,
        "count": len(entries),
    }


@router.post("/override")
async def queue_override(
    body: OverrideRequest,
    current_user: CurrentUser,
) -> dict:
    try:
        get_system(body.system_id)
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"System {body.system_id} not found.",
        ) from None

    await pg_event_bus.publish(
        channel="override_queue",
        payload={
            "system_id": body.system_id.upper(),
            "directive": body.directive,
            "reason": body.reason,
            "user_id": current_user["user_id"],
        },
    )
    return {
        "status": "queued",
        "system_id": body.system_id.upper(),
    }
