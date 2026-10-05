"""Durable/ephemeral persistence for decisions, beliefs, outcomes and world state."""
from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import text

from app.config import get_settings
from app.database import AsyncSessionLocal
from app.runtime import memory_store

settings = get_settings()


def _now() -> datetime:
    return datetime.now(UTC)


async def create_decision(record: dict[str, Any]) -> str:
    decision_id = record.get("id") or str(uuid.uuid4())
    record = {**record, "id": decision_id, "created_at": record.get("created_at") or _now()}

    if not settings.is_persistent:
        memory_store.decisions.append(record)
        del memory_store.decisions[:-500]
        return decision_id

    assert AsyncSessionLocal is not None
    async with AsyncSessionLocal() as session:
        await session.execute(
            text("""
                INSERT INTO pamasmma_decisions (
                    id, user_id, primary_system_id, objective, context, constraints,
                    evidence, memories, options, assumptions, risks, confidence,
                    certainty_band, selected_action, alternatives_rejected, owner,
                    expected_outcome, deadline, horizon_checks, status, created_at, updated_at
                ) VALUES (
                    CAST(:id AS uuid), :user_id, :primary_system_id, :objective,
                    CAST(:context AS jsonb), CAST(:constraints AS jsonb),
                    CAST(:evidence AS jsonb), CAST(:memories AS jsonb),
                    CAST(:options AS jsonb), CAST(:assumptions AS jsonb),
                    CAST(:risks AS jsonb), :confidence, :certainty_band,
                    :selected_action, CAST(:alternatives_rejected AS jsonb), :owner,
                    :expected_outcome, :deadline, CAST(:horizon_checks AS jsonb),
                    :status, :created_at, :updated_at
                )
            """),
            {
                "id": decision_id,
                "user_id": record["user_id"],
                "primary_system_id": record["primary_system_id"],
                "objective": record["objective"],
                "context": json.dumps(record.get("context", {})),
                "constraints": json.dumps(record.get("constraints", [])),
                "evidence": json.dumps(record.get("evidence", [])),
                "memories": json.dumps(record.get("memories", [])),
                "options": json.dumps(record.get("options", [])),
                "assumptions": json.dumps(record.get("assumptions", [])),
                "risks": json.dumps(record.get("risks", [])),
                "confidence": record.get("confidence", 0.5),
                "certainty_band": record.get("certainty_band", "moderate"),
                "selected_action": record["selected_action"],
                "alternatives_rejected": json.dumps(record.get("alternatives_rejected", [])),
                "owner": record.get("owner", "PAMASMMA"),
                "expected_outcome": record.get("expected_outcome", ""),
                "deadline": record.get("deadline"),
                "horizon_checks": json.dumps(record.get("horizon_checks", {})),
                "status": record.get("status", "open"),
                "created_at": record["created_at"],
                "updated_at": record["created_at"],
            },
        )
        await session.commit()
    return decision_id


async def get_decision(decision_id: str, user_id: str) -> dict[str, Any] | None:
    if not settings.is_persistent:
        return next(
            (x for x in memory_store.decisions if x["id"] == decision_id and x["user_id"] == user_id),
            None,
        )

    assert AsyncSessionLocal is not None
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text("SELECT * FROM pamasmma_decisions WHERE id = CAST(:id AS uuid) AND user_id = :user_id"),
            {"id": decision_id, "user_id": user_id},
        )
        row = result.mappings().first()
    return dict(row) if row else None


async def list_decisions(user_id: str, limit: int = 50) -> list[dict[str, Any]]:
    if not settings.is_persistent:
        rows = [x for x in memory_store.decisions if x["user_id"] == user_id]
        rows.sort(key=lambda x: x.get("created_at") or _now(), reverse=True)
        return rows[:limit]

    assert AsyncSessionLocal is not None
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text("""
                SELECT * FROM pamasmma_decisions
                WHERE user_id = :user_id
                ORDER BY created_at DESC
                LIMIT :limit
            """),
            {"user_id": user_id, "limit": limit},
        )
        return [dict(row) for row in result.mappings().all()]


async def update_decision_outcome(
    decision_id: str,
    user_id: str,
    observed_outcome: str,
    prediction_error: float | None,
) -> None:
    if not settings.is_persistent:
        for record in memory_store.decisions:
            if record["id"] == decision_id and record["user_id"] == user_id:
                record.update(
                    {
                        "observed_outcome": observed_outcome,
                        "prediction_error": prediction_error,
                        "status": "closed",
                        "updated_at": _now(),
                    }
                )
                return
        return

    assert AsyncSessionLocal is not None
    async with AsyncSessionLocal() as session:
        await session.execute(
            text("""
                UPDATE pamasmma_decisions
                SET observed_outcome = :observed_outcome,
                    prediction_error = :prediction_error,
                    status = 'closed',
                    updated_at = NOW()
                WHERE id = CAST(:id AS uuid) AND user_id = :user_id
            """),
            {
                "id": decision_id,
                "user_id": user_id,
                "observed_outcome": observed_outcome[:10000],
                "prediction_error": prediction_error,
            },
        )
        await session.commit()


async def create_outcome(record: dict[str, Any]) -> str:
    outcome_id = record.get("id") or str(uuid.uuid4())
    record = {**record, "id": outcome_id, "created_at": record.get("created_at") or _now()}

    if not settings.is_persistent:
        memory_store.outcomes.append(record)
        del memory_store.outcomes[:-500]
        return outcome_id

    assert AsyncSessionLocal is not None
    async with AsyncSessionLocal() as session:
        await session.execute(
            text("""
                INSERT INTO pamasmma_outcomes (
                    id, decision_id, user_id, expected_outcome, observed_outcome,
                    success_score, prediction_error, failure_domain, lesson, metadata, created_at
                ) VALUES (
                    CAST(:id AS uuid), CAST(:decision_id AS uuid), :user_id, :expected_outcome,
                    :observed_outcome, :success_score, :prediction_error, :failure_domain,
                    :lesson, CAST(:metadata AS jsonb), :created_at
                )
            """),
            {
                "id": outcome_id,
                "decision_id": record["decision_id"],
                "user_id": record["user_id"],
                "expected_outcome": record.get("expected_outcome", ""),
                "observed_outcome": record.get("observed_outcome", ""),
                "success_score": record.get("success_score"),
                "prediction_error": record.get("prediction_error"),
                "failure_domain": record.get("failure_domain", "unknown"),
                "lesson": record.get("lesson", ""),
                "metadata": json.dumps(record.get("metadata", {})),
                "created_at": record["created_at"],
            },
        )
        await session.commit()
    return outcome_id


async def list_beliefs(user_id: str, limit: int = 100) -> list[dict[str, Any]]:
    if not settings.is_persistent:
        rows = [x for x in memory_store.beliefs if x["user_id"] == user_id]
        rows.sort(key=lambda x: x.get("updated_at") or _now(), reverse=True)
        return rows[:limit]

    assert AsyncSessionLocal is not None
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text("""
                SELECT * FROM pamasmma_beliefs
                WHERE user_id = :user_id AND status = 'active'
                ORDER BY updated_at DESC
                LIMIT :limit
            """),
            {"user_id": user_id, "limit": limit},
        )
        return [dict(row) for row in result.mappings().all()]


async def upsert_belief(user_id: str, belief: dict[str, Any]) -> str:
    statement = belief["statement"]
    if not settings.is_persistent:
        existing = next(
            (x for x in memory_store.beliefs if x["user_id"] == user_id and x["statement"] == statement),
            None,
        )
        now = _now()
        if existing:
            existing.update(belief)
            existing["updated_at"] = now
            return str(existing["id"])
        record = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            **belief,
            "created_at": now,
            "updated_at": now,
        }
        memory_store.beliefs.append(record)
        del memory_store.beliefs[:-1000]
        return str(record["id"])

    assert AsyncSessionLocal is not None
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text("""
                SELECT id FROM pamasmma_beliefs
                WHERE user_id = :user_id AND statement = :statement
                LIMIT 1
            """),
            {"user_id": user_id, "statement": statement[:1000]},
        )
        existing = result.scalar_one_or_none()
        if existing:
            await session.execute(
                text("""
                    UPDATE pamasmma_beliefs
                    SET confidence = :confidence,
                        reliability = :reliability,
                        evidence_type = :evidence_type,
                        source = :source,
                        subject = :subject,
                        predicate = :predicate,
                        object = :object,
                        status = 'active',
                        updated_at = NOW()
                    WHERE id = :id
                """),
                {**belief, "id": existing, "statement": statement[:1000]},
            )
            await session.commit()
            return str(existing)

        belief_id = str(uuid.uuid4())
        await session.execute(
            text("""
                INSERT INTO pamasmma_beliefs (
                    id, user_id, statement, evidence_type, confidence, reliability,
                    source, subject, predicate, object, status, created_at, updated_at
                ) VALUES (
                    CAST(:id AS uuid), :user_id, :statement, :evidence_type, :confidence,
                    :reliability, :source, :subject, :predicate, :object, 'active', NOW(), NOW()
                )
            """),
            {**belief, "id": belief_id, "statement": statement[:1000]},
        )
        await session.commit()
        return belief_id


async def upsert_world_entity(
    user_id: str,
    name: str,
    entity_type: str,
    attributes: dict[str, Any],
    confidence: float,
) -> str:
    if not settings.is_persistent:
        existing = next(
            (x for x in memory_store.world_entities if x["user_id"] == user_id and x["name"].lower() == name.lower()),
            None,
        )
        now = _now()
        if existing:
            existing["attributes"] = {**existing.get("attributes", {}), **attributes}
            existing["confidence"] = max(existing.get("confidence", 0.0), confidence)
            existing["updated_at"] = now
            return str(existing["id"])
        record = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "name": name,
            "entity_type": entity_type,
            "attributes": attributes,
            "confidence": confidence,
            "created_at": now,
            "updated_at": now,
        }
        memory_store.world_entities.append(record)
        del memory_store.world_entities[:-1000]
        return str(record["id"])

    assert AsyncSessionLocal is not None
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text("""
                SELECT id FROM pamasmma_world_entities
                WHERE user_id = :user_id AND lower(name) = lower(:name)
                LIMIT 1
            """),
            {"user_id": user_id, "name": name},
        )
        existing = result.scalar_one_or_none()
        if existing:
            await session.execute(
                text("""
                    UPDATE pamasmma_world_entities
                    SET attributes = COALESCE(attributes, '{}'::jsonb) || CAST(:attributes AS jsonb),
                        confidence = GREATEST(confidence, :confidence),
                        updated_at = NOW()
                    WHERE id = :id
                """),
                {"id": existing, "attributes": json.dumps(attributes), "confidence": confidence},
            )
            await session.commit()
            return str(existing)

        entity_id = str(uuid.uuid4())
        await session.execute(
            text("""
                INSERT INTO pamasmma_world_entities (
                    id, user_id, name, entity_type, attributes, confidence, created_at, updated_at
                ) VALUES (
                    CAST(:id AS uuid), :user_id, :name, :entity_type,
                    CAST(:attributes AS jsonb), :confidence, NOW(), NOW()
                )
            """),
            {
                "id": entity_id,
                "user_id": user_id,
                "name": name,
                "entity_type": entity_type,
                "attributes": json.dumps(attributes),
                "confidence": confidence,
            },
        )
        await session.commit()
        return entity_id


async def upsert_relationship(
    user_id: str,
    subject: str,
    relation: str,
    object_name: str,
    confidence: float,
) -> str:
    if not settings.is_persistent:
        key=(user_id, subject.lower(), relation.lower(), object_name.lower())
        existing=next((x for x in memory_store.relationships if x.get("_key")==key),None)
        if existing:
            existing["confidence"]=max(existing.get("confidence",0),confidence)
            existing["updated_at"]=_now()
            return str(existing["id"])
        record={"id":str(uuid.uuid4()),"_key":key,"user_id":user_id,"subject":subject,"relation":relation,"object":object_name,"confidence":confidence,"created_at":_now(),"updated_at":_now()}
        memory_store.relationships.append(record)
        del memory_store.relationships[:-1000]
        return str(record["id"])

    assert AsyncSessionLocal is not None
    async with AsyncSessionLocal() as session:
        result=await session.execute(
            text("""
                SELECT id FROM pamasmma_world_relationships
                WHERE user_id=:user_id AND lower(subject)=lower(:subject)
                  AND relation=:relation AND lower(object)=lower(:object)
                LIMIT 1
            """),
            {"user_id":user_id,"subject":subject,"relation":relation,"object":object_name},
        )
        existing=result.scalar_one_or_none()
        if existing:
            await session.execute(
                text("UPDATE pamasmma_world_relationships SET confidence=GREATEST(confidence,:confidence), updated_at=NOW() WHERE id=:id"),
                {"id":existing,"confidence":confidence},
            )
            await session.commit()
            return str(existing)
        relationship_id=str(uuid.uuid4())
        await session.execute(
            text("""
                INSERT INTO pamasmma_world_relationships
                    (id,user_id,subject,relation,object,confidence,created_at,updated_at)
                VALUES
                    (CAST(:id AS uuid),:user_id,:subject,:relation,:object,:confidence,NOW(),NOW())
            """),
            {"id":relationship_id,"user_id":user_id,"subject":subject,"relation":relation,"object":object_name,"confidence":confidence},
        )
        await session.commit()
        return relationship_id


async def list_world_entities(user_id: str, names: list[str] | None = None, limit: int = 50) -> list[dict[str, Any]]:
    if not settings.is_persistent:
        rows=[x for x in memory_store.world_entities if x["user_id"]==user_id]
        if names:
            wanted={x.lower() for x in names}
            rows=[x for x in rows if x["name"].lower() in wanted]
        rows.sort(key=lambda x:x.get("updated_at") or _now(), reverse=True)
        return rows[:limit]

    assert AsyncSessionLocal is not None
    filters="WHERE user_id=:user_id"
    params={"user_id":user_id,"limit":limit}
    async with AsyncSessionLocal() as session:
        result=await session.execute(
            text(f"SELECT * FROM pamasmma_world_entities {filters} ORDER BY updated_at DESC LIMIT :limit"),
            params,
        )
        rows = [dict(row) for row in result.mappings().all()]
    if names:
        wanted = {value.lower() for value in names}
        rows = [row for row in rows if str(row.get("name", "")).lower() in wanted]
    return rows


async def list_outcomes(user_id: str, limit: int = 50) -> list[dict[str, Any]]:
    if not settings.is_persistent:
        rows=[x for x in memory_store.outcomes if x["user_id"]==user_id]
        rows.sort(key=lambda x:x.get("created_at") or _now(), reverse=True)
        return rows[:limit]

    assert AsyncSessionLocal is not None
    async with AsyncSessionLocal() as session:
        result=await session.execute(
            text("SELECT * FROM pamasmma_outcomes WHERE user_id=:user_id ORDER BY created_at DESC LIMIT :limit"),
            {"user_id":user_id,"limit":limit},
        )
        return [dict(row) for row in result.mappings().all()]
