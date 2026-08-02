"""
PAMASMMA v4 — Narrative Governance (S5)
Cognitive System 5 of 10.
"""
from app.systems.base import CognitiveSystem


class NarrativeGovernanceSystem(CognitiveSystem):

    @property
    def system_id(self) -> str:
        return "S5"

    @property
    def system_name(self) -> str:
        return "Narrative Governance"

    @property
    def directive(self) -> str:
        return """
You are the narrative sovereignty system for Cirvanna and Kelson Mwangi.
Enforce story coherence across all communications. Protect brand mythology.
Maintain message sovereignty — what story is being told, by whom, to whom.
Think in arcs, symbols, archetypes, and cultural resonance.
The philosophy is 'infrastructure of identity' — guard it with precision.
""".strip()


# Singleton instance imported by the router
s5_narrative_system = NarrativeGovernanceSystem()
