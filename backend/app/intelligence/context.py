"""Deterministic context assembly and sensitivity classification."""
from __future__ import annotations

import re

from app.intelligence.contracts import (
    CognitiveContext,
    IntentType,
    Sensitivity,
    TaskComplexity,
    WorldEntity,
)


class ContextAssembler:
    _SENSITIVE = (
        "password", "secret", "token", "api key", "private key", "seed phrase",
        "bank account", "credit card", "medical record", "diagnosis",
    )
    _KNOWN_SYSTEM_ENTITIES = {
        "pamasmma": "software_project",
        "cirvanna": "software_project",
        "nakima": "software_project",
        "midas-touch2": "software_project",
        "midas touch2": "software_project",
    }

    @classmethod
    def assemble(
        cls,
        messages: list[dict],
        user_id: str,
        primary_system_id: str,
    ) -> CognitiveContext:
        query = next(
            (str(m.get("content", "")).strip() for m in reversed(messages) if m.get("role") == "user"),
            "",
        )
        intent = cls._intent(query)
        sensitivity = cls._sensitivity(query)
        complexity = cls._complexity(query, intent)

        constraints = cls._constraints(query)
        goals = cls._goals(query)
        entities = cls._entities(query)
        relationships = cls._relationships(query)

        recent = [
            {"role": m["role"], "content": str(m["content"])[:8000]}
            for m in messages[-8:]
        ]
        return CognitiveContext(
            user_id=user_id,
            primary_system_id=primary_system_id.upper(),
            query=query,
            recent_messages=recent,
            objective=query,
            intent=intent,
            sensitivity=sensitivity,
            complexity=complexity,
            constraints=constraints,
            goals=goals,
            entities=entities,
            relationships=relationships,
        )

    @classmethod
    def _intent(cls, text: str) -> IntentType:
        lower = text.lower()
        if any(x in lower for x in ("implement", "build", "code", "fix", "debug", "refactor")):
            return IntentType.IMPLEMENTATION
        if any(x in lower for x in ("choose", "decide", "should we", "which is better", "priority")):
            return IntentType.DECISION
        if any(x in lower for x in ("plan", "strategy", "roadmap", "next steps", "sequence")):
            return IntentType.PLANNING
        if any(x in lower for x in ("research", "latest", "compare", "benchmark", "find evidence")):
            return IntentType.RESEARCH
        if any(x in lower for x in ("review", "audit", "assess", "critique")):
            return IntentType.REVIEW
        if any(x in lower for x in ("write", "draft", "caption", "email", "message", "script")):
            return IntentType.COMMUNICATION
        if any(x in lower for x in ("analyze", "analyse", "why", "explain")):
            return IntentType.ANALYSIS
        return IntentType.GENERAL

    @classmethod
    def _sensitivity(cls, text: str) -> Sensitivity:
        lower = text.lower()
        return Sensitivity.SENSITIVE if any(token in lower for token in cls._SENSITIVE) else Sensitivity.STANDARD

    @classmethod
    def _complexity(cls, text: str, intent: IntentType) -> TaskComplexity:
        lower = text.lower()
        if intent in {IntentType.RESEARCH, IntentType.REVIEW} or len(text) > 1800:
            return TaskComplexity.COMPLEX
        if intent in {IntentType.PLANNING, IntentType.DECISION} or any(
            token in lower for token in ("architecture", "system", "strategy", "investor", "business model")
        ):
            return TaskComplexity.STRATEGIC
        if intent in {IntentType.IMPLEMENTATION, IntentType.ANALYSIS} or len(text) > 600:
            return TaskComplexity.MODERATE
        return TaskComplexity.ROUTINE

    @staticmethod
    def _constraints(text: str) -> list[str]:
        constraints: list[str] = []
        for match in re.finditer(
            r"(?:must|need to|needs to|avoid|cannot|can't|only|under|within|before|without)[^.\n;]{0,180}",
            text,
            flags=re.IGNORECASE,
        ):
            value = " ".join(match.group(0).split())
            if value not in constraints:
                constraints.append(value)
        return constraints[:8]

    @staticmethod
    def _goals(text: str) -> list[str]:
        goals: list[str] = []
        for match in re.finditer(
            r"(?:to|for)s+(?:increase|reduce|improve|build|create|launch|complete|achieve|reach|optimize)[^.\n;]{0,180}",
            text,
            flags=re.IGNORECASE,
        ):
            value = " ".join(match.group(0).split())
            if value not in goals:
                goals.append(value)
        return goals[:6]

    @classmethod
    def _entities(cls, text: str) -> list[WorldEntity]:
        found: dict[str, WorldEntity] = {}
        lower = text.lower()
        for key, kind in cls._KNOWN_SYSTEM_ENTITIES.items():
            if key in lower:
                found[key.title()] = WorldEntity(name=key.title(), entity_type=kind, confidence=0.95)

        for candidate in re.findall(r"[A-Z][A-Za-z0-9&-]{2,}", text):
            normalized = candidate.strip(".,:;!?")
            if normalized.lower() in {"I", "The", "You", "We", "Can"}:
                continue
            found.setdefault(normalized, WorldEntity(name=normalized, entity_type="named_concept", confidence=0.7))
        return list(found.values())[:12]

    @staticmethod
    def _relationships(text: str):
        from app.intelligence.contracts import Relationship
        patterns = (
            (r"\b([A-Za-z][A-Za-z0-9&- ]{1,50})\s+works with\s+([A-Za-z][A-Za-z0-9&- ]{1,50})\b", "works_with"),
            (r"\b([A-Za-z][A-Za-z0-9&- ]{1,50})\s+is\s+(?:a|an)\s+partner of\s+([A-Za-z][A-Za-z0-9&- ]{1,50})\b", "partner_of"),
            (r"\b([A-Za-z][A-Za-z0-9&- ]{1,50})\s+owns\s+([A-Za-z][A-Za-z0-9&- ]{1,50})\b", "owns"),
            (r"\b([A-Za-z][A-Za-z0-9&- ]{1,50})\s+serves\s+([A-Za-z][A-Za-z0-9&- ]{1,50})\b", "serves"),
        )
        relationships=[]
        for pattern, relation in patterns:
            for match in re.finditer(pattern, text, flags=re.IGNORECASE):
                relationships.append(
                    Relationship(
                        subject=" ".join(match.group(1).split()),
                        relation=relation,
                        object=" ".join(match.group(2).split()),
                        confidence=0.85,
                    )
                )
        return relationships[:8]
