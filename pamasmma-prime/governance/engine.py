class GovernanceEngine:
    """
    Pamasmma Prime Governance Engine

    This layer enforces system-wide constraints on autonomy.

    It decides whether a proposed action is:
    - allowed
    - allowed with constraints
    - rejected
    """

    def __init__(self):
        self.hard_constraints = [
            "no_self_destruction",
            "no_unbounded_self_modification",
            "no_external_system_takeover"
        ]

        self.soft_constraints = [
            "resource_efficiency",
            "traceability_required",
            "human_override_allowed"
        ]

    def evaluate(self, action: dict) -> dict:
        """
        Evaluate whether an action is permitted.
        """

        if not action:
            return {"status": "rejected", "reason": "empty_action"}

        # Hard constraint check (simplified baseline)
        if action.get("type") in self.hard_constraints:
            return {
                "status": "rejected",
                "reason": "violates_hard_constraint"
            }

        # Default allow with audit trail requirement
        return {
            "status": "allowed",
            "constraints": self.soft_constraints,
            "audit": True
        }
