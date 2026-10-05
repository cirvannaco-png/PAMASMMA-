"""Specialist routing across PAMASMMA S1–S10."""
from app.intelligence.contracts import CognitiveContext, IntentType, SpecialistAssignment


class SpecialistRouter:
    _INTENT_MAP = {
        IntentType.COMMUNICATION: [("S9", 0.9), ("S5", 0.65), ("S8", 0.45)],
        IntentType.RESEARCH: [("S2", 0.8), ("S6", 0.65), ("S10", 0.5)],
        IntentType.DECISION: [("S1", 1.0), ("S2", 0.65), ("S10", 0.7), ("S7", 0.45)],
        IntentType.PLANNING: [("S1", 1.0), ("S10", 0.8), ("S2", 0.55), ("S7", 0.45)],
        IntentType.IMPLEMENTATION: [("S1", 0.85), ("S7", 0.55)],
        IntentType.REVIEW: [("S7", 0.85), ("S1", 0.7), ("S10", 0.45)],
        IntentType.ANALYSIS: [("S1", 0.8), ("S6", 0.6), ("S10", 0.55)],
        IntentType.GENERAL: [("S1", 0.8)],
    }

    _KEYWORD_RULES = (
        (("market", "campaign", "positioning", "customer", "growth"), "S2", 0.25),
        (("investor", "partner", "relationship", "stakeholder", "network"), "S3", 0.25),
        (("creator", "content", "audience", "distribution", "viral"), "S4", 0.2),
        (("story", "narrative", "brand", "mythology", "identity"), "S5", 0.2),
        (("psychology", "behavior", "segment", "emotion", "persona"), "S6", 0.2),
        (("consistent", "drift", "calibrate", "personality", "behavior"), "S7", 0.2),
        (("persuade", "conversion", "influence", "pitch", "negotiat"), "S8", 0.2),
        (("voice", "tone", "script", "speak", "presence"), "S9", 0.2),
        (("vision", "legacy", "10-year", "category", "long-term"), "S10", 0.3),
    )

    @classmethod
    def route(cls, context: CognitiveContext) -> list[SpecialistAssignment]:
        scores: dict[str, tuple[float, list[str]]] = {}
        for system_id, weight in cls._INTENT_MAP.get(context.intent, [("S1", 0.8)]):
            scores[system_id] = (weight, ["intent match"])

        lower = context.query.lower()
        for keywords, system_id, bonus in cls._KEYWORD_RULES:
            if any(keyword in lower for keyword in keywords):
                score, reasons = scores.get(system_id, (0.0, []))
                scores[system_id] = (min(1.0, score + bonus), reasons + ["domain signal"])

        # The primary domain is always present. S1 is orchestration, not mandatory
        # voting power; routing is evidence-weighted rather than a fixed committee.
        if context.primary_system_id not in scores:
            scores[context.primary_system_id] = (0.95, ["primary system"])
        assignments = [
            SpecialistAssignment(
                system_id=system_id,
                reason="; ".join(reasons),
                weight=score,
                required=(system_id == context.primary_system_id or system_id == "S1"),
            )
            for system_id, (score, reasons) in scores.items()
        ]
        assignments.sort(key=lambda item: (-item.weight, item.system_id))
        if context.primary_system_id != "S1":
            assignments = [item for item in assignments if item.system_id != "S1"] + [item for item in assignments if item.system_id == "S1"]
        return assignments[:5]
