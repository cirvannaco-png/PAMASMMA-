"""User/project world model and lightweight relationship graph."""
from __future__ import annotations

from app.intelligence.contracts import CognitiveContext
from app.intelligence.persistence import (
    list_world_entities,
    upsert_relationship,
    upsert_world_entity,
)


class WorldModel:
    async def observe(self, context: CognitiveContext) -> None:
        scoped_user_id = context.memory_scope_id or context.user_id
        for entity in context.entities:
            await upsert_world_entity(
                user_id=scoped_user_id,
                name=entity.name,
                entity_type=entity.entity_type,
                attributes={
                    "last_seen_query": context.query[:300],
                    "primary_system": context.primary_system_id,
                },
                confidence=entity.confidence,
            )
        for relationship in context.relationships:
            await upsert_relationship(
                user_id=context.user_id,
                subject=relationship.subject,
                relation=relationship.relation,
                object_name=relationship.object,
                confidence=relationship.confidence,
            )

    async def hydrate(self, context: CognitiveContext) -> list[dict]:
        names = [entity.name for entity in context.entities]
        scoped_user_id = context.memory_scope_id or context.user_id
        return await list_world_entities(scoped_user_id, names=names or None, limit=30)
