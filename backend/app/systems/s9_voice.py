"""
PAMASMMA v4 — Voice & Presence (S9)
Cognitive System 9 of 10.
"""
from app.systems.base import CognitiveSystem


class VoiceAndPresenceSystem(CognitiveSystem):

    @property
    def system_id(self) -> str:
        return "S9"

    @property
    def system_name(self) -> str:
        return "Voice & Presence"

    @property
    def directive(self) -> str:
        return """
You are the voice and presence amplification system.
Synthesize Kelson's tone across written, verbal, and digital contexts.
Calibrate delivery cadence for keynotes, interviews, social, and correspondence.
Build presence as a compounding asset — each communication reinforces the brand.
Output must be concrete: scripts, openings, framings, not abstract style notes.
""".strip()


# Singleton instance imported by the router
s9_voice_system = VoiceAndPresenceSystem()
