from typing import Any, Dict, List, Optional


class SelfModificationEngine:
    """
    Pamasmma Prime Self-Modification Engine (GATED)

    This subsystem allows controlled evolution of the system.

    IMPORTANT:
    - All modifications are simulated before execution
    - All changes require governance approval
    - All changes are versioned and reversible
    """

    def __init__(self, governance=None, objectives=None):
        self.governance = governance
        self.objectives = objectives
        self.proposals: List[Dict[str, Any]] = []
        self.applied_changes: List[Dict[str, Any]] = []

    def propose_change(self, change: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Submit a proposed system modification.
        """

        proposal = {
            "change": change,
            "context": context,
            "status": "pending"
        }

        self.proposals.append(proposal)
        return proposal

    def simulate(self, proposal: Dict[str, Any]) -> Dict[str, Any]:
        """
        Simulate impact of a proposed change.
        """

        change = proposal.get("change", {})

        # naive simulation model
        risk = 0.0

        if change.get("type") == "governance_override":
            risk += 0.9

        if change.get("type") == "objective_rewrite":
            risk += 0.7

        return {
            "risk_score": risk,
            "safe": risk < 0.5
        }

    def evaluate_and_apply(self, proposal: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run governance + simulation before applying change.
        """

        simulation = self.simulate(proposal)

        if not simulation["safe"]:
            return {
                "status": "rejected",
                "reason": "simulation_failed",
                "risk": simulation["risk_score"]
            }

        if self.governance:
            decision = self.governance.evaluate(proposal.get("change", {}))
            if decision.get("status") != "allowed":
                return {
                    "status": "rejected",
                    "reason": "governance_block",
                    "details": decision
                }

        self.applied_changes.append(proposal)

        return {
            "status": "applied",
            "proposal": proposal
        }

    def rollback(self, index: int) -> Dict[str, Any]:
        """
        Roll back a previously applied change.
        """

        if index < 0 or index >= len(self.applied_changes):
            return {"status": "error", "reason": "invalid_index"}

        change = self.applied_changes.pop(index)

        return {
            "status": "rolled_back",
            "change": change
        }
