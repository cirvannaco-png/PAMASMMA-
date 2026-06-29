from typing import Any, Dict, List

class PlanningEngine:
    """
    Pamasmma Prime Multi-Step Planning Engine

    Converts single decisions into multi-step execution trajectories.
    This is the reasoning layer that enables foresight.
    """

    def __init__(self, objective_system=None, governance=None):
        self.objective_system = objective_system
        self.governance = governance

    def generate_plan(self, state: Dict[str, Any], goal: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Create a multi-step plan from a goal.
        """

        # Step 1: naive decomposition (baseline)
        raw_steps = self._decompose(goal)

        # Step 2: score steps using objective system
        scored_steps = []
        for step in raw_steps:
            score = 0.0

            if self.objective_system:
                score = self.objective_system.evaluate(state, step)

            scored_steps.append({
                "step": step,
                "score": score
            })

        # Step 3: sort by utility
        scored_steps.sort(key=lambda x: x["score"], reverse=True)

        # Step 4: governance filtering
        if self.governance:
            filtered = []
            for item in scored_steps:
                decision = self.governance.evaluate(item["step"])
                if decision["status"] == "allowed":
                    filtered.append(item["step"])
        else:
            filtered = [s["step"] for s in scored_steps]

        # Step 5: return execution plan
        return filtered

    def _decompose(self, goal: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Break goal into primitive steps (placeholder logic).
        """
        if not goal:
            return [{"type": "noop"}]

        return [
            {"type": "analyze", "payload": goal},
            {"type": "process", "payload": goal},
            {"type": "execute", "payload": goal}
        ]
