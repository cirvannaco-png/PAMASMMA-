"""
PAMASMMA v4.2 — Behavioral Consistency (S7)
Cognitive System 7 of 10.
"""
from app.systems.base import CognitiveSystem


class BehavioralConsistencySystem(CognitiveSystem):

    @property
    def system_id(self) -> str:
        return "S7"

    @property
    def system_name(self) -> str:
        return "Behavioral Consistency"

    @property
    def directive(self) -> str:
        return """
You are the behavioral consistency and metacognitive governance system.
Audit outputs for coherence with the personality baseline, evidence status,
confidence, contradictions and strategic alignment. Flag behavioral drift,
overconfidence, unsupported certainty, and reasoning inconsistencies.
Issue recalibration directives without overriding material evidence or safety
constraints.
""".strip()


s7_behavioral_system = BehavioralConsistencySystem()
