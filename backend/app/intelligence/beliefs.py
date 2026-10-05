"""Belief extraction and contradiction resolution."""
from __future__ import annotations

import re

from app.intelligence.contracts import Belief, CognitiveContext, EvidenceType
from app.intelligence.critic import ContradictionChecker


class BeliefResolver:
    _CLAIM = re.compile(
        r"^(?P<subject>[A-Za-z][A-Za-z0-9 _-]{1,50})\s+"
        r"(?P<predicate>is|has|uses|prefers|wants|needs|owns|serves)\s+"
        r"(?P<object>[^.?!]{2,120})$",
        re.IGNORECASE,
    )

    @classmethod
    def extract_user_beliefs(cls, context: CognitiveContext) -> list[Belief]:
        text = " ".join(
            message["content"] for message in context.recent_messages
            if message.get("role") == "user"
        ).strip()
        if not text or "?" in text:
            return []

        claims=[]
        for sentence in re.split(r"[.\n]+", text):
            sentence=" ".join(sentence.split())
            match=cls._CLAIM.match(sentence)
            if not match:
                continue
            claims.append(
                Belief(
                    statement=sentence,
                    evidence_type=EvidenceType.FACT,
                    confidence=0.88,
                    reliability=0.75,
                    source="explicit_user_statement",
                    subject=match.group("subject"),
                    predicate=match.group("predicate").lower(),
                    object=match.group("object"),
                )
            )
        return claims[:10]

    @classmethod
    def find_contradictions(
        cls,
        new_beliefs: list[Belief],
        existing: list[dict],
    ) -> list[str]:
        contradictions=[]
        for belief in new_beliefs:
            for previous in existing:
                same_subject = (
                    belief.subject and previous.get("subject")
                    and belief.subject.lower() == str(previous["subject"]).lower()
                )
                same_predicate = (
                    belief.predicate and previous.get("predicate")
                    and belief.predicate.lower() == str(previous["predicate"]).lower()
                )
                if not (same_subject and same_predicate):
                    continue
                previous_statement = str(previous.get("statement",""))
                if previous_statement == belief.statement:
                    continue
                if ContradictionChecker.text_contradiction(previous_statement, belief.statement):
                    contradictions.append(
                        f"Conflict: '{previous_statement}' vs '{belief.statement}'"
                    )
                elif str(previous.get("object","")).lower() != str(belief.object or "").lower():
                    contradictions.append(
                        f"Competing belief: '{previous_statement}' vs '{belief.statement}'"
                    )
        return contradictions[:10]

    @staticmethod
    def confidence_after_conflict(
        base: float,
        contradiction_count: int,
    ) -> float:
        return max(0.1, min(0.95, base - (0.12 * contradiction_count)))
