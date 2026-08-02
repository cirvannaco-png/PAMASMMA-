"""
PAMASMMA v4 — Marketing Intelligence (S2)
Cognitive System 2 of 10.
"""
from app.systems.base import CognitiveSystem


class MarketingIntelligenceSystem(CognitiveSystem):

    @property
    def system_id(self) -> str:
        return "S2"

    @property
    def system_name(self) -> str:
        return "Marketing Intelligence"

    @property
    def directive(self) -> str:
        return """
You are the marketing intelligence system for Cirvanna.
Analyze brand positioning, decode market signals, synthesize campaign intelligence.
Operate in the context of fashion-tech across East Africa and global emerging markets.
Think in brand equity, cultural resonance, and distribution leverage.
Every output must be actionable and tied to a measurable outcome.
""".strip()


# Singleton instance imported by the router
s2_marketing_system = MarketingIntelligenceSystem()
