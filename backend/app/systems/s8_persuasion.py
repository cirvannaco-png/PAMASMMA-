"""
PAMASMMA v4 — Persuasion Governance (S8)
Cognitive System 8 of 10.
"""
from app.systems.base import CognitiveSystem


class PersuasionGovernanceSystem(CognitiveSystem):

    @property
    def system_id(self) -> str:
        return "S8"

    @property
    def system_name(self) -> str:
        return "Persuasion Governance"

    @property
    def directive(self) -> str:
        return """
You are the persuasion governance system.
Architect ethical influence strategies. Model conversion psychology.
Audit persuasion integrity — distinguish principled influence from manipulation.
Apply behavioral economics, social proof, and commitment mechanics responsibly.
Every persuasion tactic must pass the ethical governance test before deployment.
""".strip()


# Singleton instance imported by the router
s8_persuasion_system = PersuasionGovernanceSystem()
