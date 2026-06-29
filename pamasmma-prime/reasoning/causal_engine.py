from typing import Any, Dict, List


class CausalReasoningEngine:
    """
    Causal reasoning module for Pamasmma Prime.

    Extracts directional relationships from event sequences.
    """

    def __init__(self):
        self.history: List[Dict[str, Any]] = []
        self.relations: List[tuple] = []

    def observe(self, event: Dict[str, Any]) -> None:
        self.history.append(event)

    def infer(self) -> List[tuple]:
        if len(self.history) < 2:
            return []

        inferred = []

        for i in range(len(self.history) - 1):
            a = self.history[i].get("type", "unknown")
            b = self.history[i + 1].get("type", "unknown")

            if a != b:
                inferred.append((a, b))

        self.relations.extend(inferred)
        return inferred

    def get_relations(self) -> List[tuple]:
        return self.relations
