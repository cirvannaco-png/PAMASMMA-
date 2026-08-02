"""
PAMASMMA v4 — Audience Psychology (S6)
Cognitive System 6 of 10.
"""
from app.systems.base import CognitiveSystem


class AudiencePsychologySystem(CognitiveSystem):

    @property
    def system_id(self) -> str:
        return "S6"

    @property
    def system_name(self) -> str:
        return "Audience Psychology"

    @property
    def directive(self) -> str:
        return """
You are the audience psychology system.
Model behavioral patterns at population and segment level.
Map sentiment dynamics, identity resonance signals, and emotional triggers.
Think like a behavioral economist with deep fashion and cultural intelligence.
Output must translate psychological insight into product, copy, or campaign decisions.
""".strip()


# Singleton instance imported by the router
s6_audience_system = AudiencePsychologySystem()
