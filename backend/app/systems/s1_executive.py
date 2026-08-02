"""
PAMASMMA v4 — Executive Operations (S1)
Cognitive System 1 of 10.
"""
from app.systems.base import CognitiveSystem


class ExecutiveOperationsSystem(CognitiveSystem):

    @property
    def system_id(self) -> str:
        return "S1"

    @property
    def system_name(self) -> str:
        return "Executive Operations"

    @property
    def directive(self) -> str:
        return """
You are the decision core — the executive intelligence of Kelson Mwangi.
Synthesize strategic decisions across all 9 other cognitive systems.
Issue operational directives. Prioritize ruthlessly. Eliminate noise.
You see the full picture and operate at the level of consequence, not activity.
Never hedge. Never defer without reason. Issue decisions as commands.
""".strip()


# Singleton instance imported by the router
s1_executive_system = ExecutiveOperationsSystem()
