"""
PAMASMMA v4 — Systems Registry
Central registry mapping system IDs to singleton instances.
Import from here rather than individual modules.
"""
from app.systems.s1_executive   import s1_executive_system
from app.systems.s2_marketing   import s2_marketing_system
from app.systems.s3_relationship import s3_relationship_system
from app.systems.s4_creator     import s4_creator_system
from app.systems.s5_narrative   import s5_narrative_system
from app.systems.s6_audience    import s6_audience_system
from app.systems.s7_behavioral  import s7_behavioral_system
from app.systems.s8_persuasion  import s8_persuasion_system
from app.systems.s9_voice       import s9_voice_system
from app.systems.s10_strategic  import s10_strategic_system
from app.systems.base import CognitiveSystem

SYSTEMS: dict[str, CognitiveSystem] = {
    "S1": s1_executive_system,
    "S2": s2_marketing_system,
    "S3": s3_relationship_system,
    "S4": s4_creator_system,
    "S5": s5_narrative_system,
    "S6": s6_audience_system,
    "S7": s7_behavioral_system,
    "S8": s8_persuasion_system,
    "S9": s9_voice_system,
    "S10": s10_strategic_system,
}

SYSTEM_METADATA = [
    {"id": "S1",  "name": "Executive Operations",    "color": "#6B3FFB"},
    {"id": "S2",  "name": "Marketing Intelligence",  "color": "#00D4FF"},
    {"id": "S3",  "name": "Relationship Management", "color": "#D4AF37"},
    {"id": "S4",  "name": "Creator Economy",         "color": "#3BFFA0"},
    {"id": "S5",  "name": "Narrative Governance",    "color": "#FF5B8B"},
    {"id": "S6",  "name": "Audience Psychology",     "color": "#FF8C42"},
    {"id": "S7",  "name": "Behavioral Consistency",  "color": "#A97FFF"},
    {"id": "S8",  "name": "Persuasion Governance",   "color": "#FF4D6D"},
    {"id": "S9",  "name": "Voice & Presence",        "color": "#5BFFD0"},
    {"id": "S10", "name": "Strategic Narrative",     "color": "#FFD700"},
]


def get_system(system_id: str) -> CognitiveSystem:
    system = SYSTEMS.get(system_id.upper())
    if not system:
        raise KeyError(f"Unknown cognitive system: {system_id}")
    return system
