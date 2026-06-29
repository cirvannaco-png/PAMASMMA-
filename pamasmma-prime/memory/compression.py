from typing import Any, Dict, List


class MemoryCompressionEngine:
    """
    Pamasmma Prime Memory Compression System

    Converts raw episodic history into compact semantic representations.
    This is the transition layer between experience and intelligence.
    """

    def __init__(self):
        self.episodic_memory: List[Dict[str, Any]] = []
        self.semantic_memory: List[Dict[str, Any]] = []

    def ingest(self, event: Dict[str, Any]) -> None:
        """
        Store raw experience (episodic layer).
        """
        self.episodic_memory.append(event)

    def compress(self) -> Dict[str, Any]:
        """
        Convert episodic memory into semantic knowledge.
        """
        if not self.episodic_memory:
            return {"status": "empty"}

        # naive compression: extract recurring action patterns
        action_counts = {}

        for event in self.episodic_memory:
            action = str(event.get("action", "unknown"))
            action_counts[action] = action_counts.get(action, 0) + 1

        summary = {
            "total_events": len(self.episodic_memory),
            "dominant_actions": sorted(action_counts.items(), key=lambda x: x[1], reverse=True),
        }

        self.semantic_memory.append(summary)
        self.episodic_memory.clear()

        return summary

    def retrieve(self) -> List[Dict[str, Any]]:
        """
        Return compressed knowledge state.
        """
        return self.semantic_memory
