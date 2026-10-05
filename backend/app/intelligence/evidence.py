"""Evidence policy: determine when a conclusion needs external verification."""
from app.intelligence.contracts import CognitiveContext, VerificationIssue


class EvidenceGate:
    CURRENT_MARKERS = (
        "today",
        "latest",
        "now",
        "price",
        "market",
        "news",
        "schedule",
        "available",
        "recent",
    )

    def assess(
        self,
        context: CognitiveContext,
        response: str = "",
    ) -> tuple[str, list[VerificationIssue]]:
        lower = " ".join((context.query, response)).lower()
        if context.intent.value == "research" or any(
            marker in lower for marker in self.CURRENT_MARKERS
        ):
            return (
                "requires_external_evidence",
                [
                    VerificationIssue(
                        severity="medium",
                        category="external_evidence",
                        message="Time-sensitive or research claims require external evidence before being treated as facts.",
                    )
                ],
            )
        return "structural_only", []
