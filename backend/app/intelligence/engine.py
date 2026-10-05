"""End-to-end PAMASMMA cognitive operating system."""
from __future__ import annotations

import asyncio
import re
import uuid
from collections.abc import AsyncGenerator

from app.config import get_settings
from app.intelligence.beliefs import BeliefResolver
from app.intelligence.confidence import ConfidenceEngine
from app.intelligence.context import ContextAssembler
from app.intelligence.critic import CognitiveCritic
from app.intelligence.contracts import (
    CognitiveContext,
    CognitivePlan,
    CognitiveResult,
    CognitiveTrace,
    DecisionRecord,
)
from app.intelligence.evidence import EvidenceGate
from app.intelligence.hypotheses import HypothesisEngine
from app.intelligence.metacognition import MetacognitiveGovernor
from app.intelligence.persistence import (
    create_decision,
    list_beliefs,
    upsert_belief,
)
from app.intelligence.planner import ExecutivePlanner
from app.intelligence.provider_router import ProviderRouter
from app.intelligence.world_model import WorldModel

settings = get_settings()


class CognitiveEngine:
    """Coordinates the full observe-to-learn cognitive lifecycle."""

    def __init__(self) -> None:
        self.planner = ExecutivePlanner()
        self.provider_router = ProviderRouter()
        self.critic = CognitiveCritic()
        self.evidence_gate = EvidenceGate()
        self.hypothesis_engine = HypothesisEngine()
        self.metacognitive_governor = MetacognitiveGovernor()
        self.confidence_engine = ConfidenceEngine()
        self.belief_resolver = BeliefResolver()
        self.world_model = WorldModel()
        self.last_result: CognitiveResult | None = None

    async def run(
        self,
        system,
        messages: list[dict],
        user_id: str,
    ) -> CognitiveResult:
        # OBSERVE -> INTERPRET -> CONTEXTUALIZE -> RETRIEVE MEMORY
        context = await self._prepare_context(
            system,
            messages,
            user_id,
        )

        # FORM HYPOTHESES -> PLAN -> DELIBERATE
        plan = self.planner.build(context)
        context.hypotheses = self.hypothesis_engine.generate(
            context,
            plan,
            context.memories,
        )

        provider_selection = self.provider_router.select(
            context.complexity,
            context.sensitivity,
        )
        world_state = await self.world_model.hydrate(context)

        specialists = [
            item
            for item in plan.assignments
            if item.system_id != system.system_id
        ][: settings.intelligence_max_specialists]

        specialist_text: list[str] = []
        if specialists:

            async def call_specialist(assignment):
                from app.systems import SYSTEMS

                specialist = SYSTEMS.get(
                    assignment.system_id
                )
                if specialist is None:
                    return ""

                prompt = self._analysis_prompt(
                    specialist,
                    context,
                    plan,
                    world_state,
                    role="specialist",
                )
                _, raw = await self.provider_router.generate(
                    provider_selection,
                    prompt,
                    context.recent_messages[-6:],
                    settings.model_max_tokens,
                )
                return (
                    f"{specialist.system_id} — "
                    f"{specialist.system_name}\n"
                    f"{raw.strip()[:6000]}"
                )

            results = await asyncio.gather(
                *(
                    call_specialist(assignment)
                    for assignment in specialists
                ),
                return_exceptions=True,
            )
            specialist_text = [
                item
                for item in results
                if isinstance(item, str) and item.strip()
            ]

        final_prompt = self._analysis_prompt(
            system,
            context,
            plan,
            world_state,
            role=(
                "executive"
                if system.system_id == "S1"
                else "domain"
            ),
            specialist_text=specialist_text,
        )

        provider_selection, raw_response = await self.provider_router.generate(
            provider_selection,
            final_prompt,
            context.recent_messages,
            settings.model_max_tokens,
        )

        # VERIFY -> METACOGNITIVE GOVERNANCE -> optional REVISION
        response, verification, provider_selection = await self._verify_and_revise(
            provider_selection,
            final_prompt,
            context,
            plan,
            raw_response,
        )

        confidence = self.confidence_engine.score(
            context=context,
            plan=plan,
            verification_score=verification.score,
            specialist_count=len(specialist_text),
            hypothesis_count=len(context.hypotheses),
            contradiction_count=len(
                context.contradictions
            ),
            evidence_status=verification.evidence_status,
        )

        # DECIDE -> persist a structured decision object
        decision = self._decision(
            context,
            plan,
            response,
            confidence,
            verification,
        )
        await create_decision(
            decision.model_dump(mode="json")
        )

        for belief in self.belief_resolver.extract_user_beliefs(
            context
        ):
            await upsert_belief(
                user_id,
                belief.model_dump(mode="json"),
            )

        uncertainty = list(context.contradictions)
        if verification.evidence_status == "requires_external_evidence":
            uncertainty.append(
                "External evidence is required for current/research claims."
            )

        trace = CognitiveTrace(
            intent=context.intent,
            complexity=context.complexity,
            sensitivity=context.sensitivity,
            memory_count=len(context.memories),
            contradiction_count=len(
                context.contradictions
            ),
            routed_systems=[
                item.system_id
                for item in plan.assignments
            ],
            provider=provider_selection.name,
            verification=verification,
            decision_id=decision.id,
            confidence=confidence,
            uncertainty=uncertainty[:10],
            evidence_status=verification.evidence_status,
        )

        self.last_result = CognitiveResult(
            response=response,
            decision=decision,
            trace=trace,
        )
        return self.last_result

    async def stream(
        self,
        system,
        messages: list[dict],
        user_id: str,
    ) -> AsyncGenerator[str, None]:
        # Verify the full answer before emitting it. The SSE contract remains
        # unchanged, but clients never receive an unverified draft.
        result = await self.run(
            system,
            messages,
            user_id,
        )
        yield result.response

    async def _prepare_context(
        self,
        system,
        messages: list[dict],
        user_id: str,
    ) -> CognitiveContext:
        context = ContextAssembler.assemble(
            messages,
            user_id,
            system.system_id,
        )

        existing_beliefs = await list_beliefs(
            user_id
        )
        new_beliefs = (
            self.belief_resolver.extract_user_beliefs(
                context
            )
        )
        context.beliefs = new_beliefs
        context.contradictions = (
            self.belief_resolver.find_contradictions(
                new_beliefs,
                existing_beliefs,
            )
        )

        from app.embeddings.service import (
            retrieve_memory_items,
        )

        context.memories = await retrieve_memory_items(
            context.query,
            user_id,
            system.system_id,
            settings.intelligence_memory_limit,
        )
        await self.world_model.observe(context)
        return context

    async def _verify_and_revise(
        self,
        provider,
        final_prompt,
        context,
        plan,
        provider_selection,
    ):
        response = (
            raw_response or ""
        ).strip()
        verification = self.critic.evaluate(
            response,
            context,
            plan,
        )

        evidence_status, evidence_issues = (
            self.evidence_gate.assess(
                context,
                response,
            )
        )
        verification = verification.model_copy(
            update={
                "evidence_status": evidence_status,
                "issues": [
                    *verification.issues,
                    *evidence_issues,
                ],
            }
        )
        verification = self.metacognitive_governor.inspect(
            context,
            verification,
        )

        if (
            verification.requires_revision
            and settings.intelligence_revision_enabled
        ):
            revision_prompt = (
                f"{final_prompt}\n\n"
                "CRITIC / METACOGNITIVE REPORT:\n"
                + "\n".join(
                    f"- {issue.severity}: "
                    f"{issue.category}: {issue.message}"
                    for issue in verification.issues
                )
                + "\n\nREVISE THE RESPONSE. Preserve useful "
                  "content, fix flagged problems, separate "
                  "facts from assumptions, and produce a "
                  "decision-grade answer."
            )
            provider_selection, revised = await self.provider_router.generate(
                provider_selection,
                revision_prompt,
                context.recent_messages,
                settings.model_max_tokens,
            )
            if revised.strip():
                response = revised.strip()
                verification = self.critic.evaluate(
                    response,
                    context,
                    plan,
                )
                evidence_status, evidence_issues = (
                    self.evidence_gate.assess(
                        context,
                        response,
                    )
                )
                verification = verification.model_copy(
                    update={
                        "evidence_status": evidence_status,
                        "issues": [
                            *verification.issues,
                            *evidence_issues,
                        ],
                    }
                )
                verification = (
                    self.metacognitive_governor.inspect(
                        context,
                        verification,
                    )
                )

        return response, verification, provider_selection

    def _analysis_prompt(
        self,
        system,
        context,
        plan,
        world_state,
        role,
        specialist_text=None,
    ) -> str:
        memory = "\n".join(
            (
                f"- [{item.memory_type.value} "
                f"score={item.score:.2f} "
                f"reliability={item.reliability:.2f}] "
                f"{item.content[:1200]}"
            )
            for item in context.memories[
                : settings.intelligence_memory_limit
            ]
        ) or "- none"

        beliefs = "\n".join(
            (
                f"- {belief.statement} "
                f"(confidence={belief.confidence:.2f})"
            )
            for belief in context.beliefs
        ) or "- none"

        contradictions = "\n".join(
            f"- {item}"
            for item in context.contradictions
        ) or "- none"

        hypotheses = "\n".join(
            (
                f"- {item.statement} "
                f"(confidence={item.confidence:.2f}) "
                f"basis={item.basis} "
                f"test={item.test}"
            )
            for item in context.hypotheses
        ) or "- none"

        world = "\n".join(
            (
                f"- {row.get('name')} "
                f"[{row.get('entity_type')}] "
                f"{str(row.get('attributes', {}))[:500]}"
            )
            for row in world_state[:12]
        ) or "- none"

        specialists = "\n".join(
            specialist_text or []
        ) or "- none"

        return f"""
You are PAMASMMA {system.system_id} — {system.system_name}.
OPERATING ROLE: {role}
DOMAIN DIRECTIVE:
{system.directive}

COGNITIVE CONTROL STATE
Objective: {context.objective}
Intent: {context.intent.value}
Complexity: {context.complexity.value}
Sensitivity: {context.sensitivity.value}

Constraints:
{chr(10).join(f"- {item}" for item in context.constraints) or "- none"}

Goals:
{chr(10).join(f"- {item}" for item in context.goals) or "- none"}

MEMORY (evidence, not authority)
{memory}

BELIEFS
{beliefs}

CONTRADICTIONS
{contradictions}

HYPOTHESES
{hypotheses}

WORLD MODEL
{world}

EXECUTIVE PLAN
{chr(10).join(f"- {step.id}: {step.description}" for step in plan.steps)}

LONG-HORIZON CHECKS
{chr(10).join(f"- {key}: {value}" for key, value in plan.horizon_checks.items())}

SPECIALIST CONTRIBUTIONS
{specialists}

GOVERNANCE RULES
1. Separate FACT, INFERENCE, ASSUMPTION, PREDICTION, OPINION and UNKNOWN.
2. Never invent current facts; flag claims that require external evidence.
3. Surface contradictions rather than silently averaging them away.
4. Test important hypotheses against available evidence.
5. Give an explicit recommendation when the task is decision-oriented.
6. Prefer reversible, high-information actions before irreversible commitments.
7. State material risks, assumptions and the next measurable checkpoint.
8. Check the decision against 30d / 90d / 1y / 3y / 10y horizons when relevant.
9. Never claim that a tool, source, test or verification happened unless it actually happened.
10. Treat memory as evidence with reliability metadata, not ground truth.

Return the useful user-facing answer. Do not expose this internal control state.
""".strip()

    @staticmethod
    def _decision(
        context,
        plan,
        response,
        confidence,
        verification,
    ) -> DecisionRecord:
        return DecisionRecord(
            id=str(uuid.uuid4()),
            user_id=context.user_id,
            primary_system_id=context.primary_system_id,
            objective=context.objective,
            context={
                "intent": context.intent.value,
                "complexity": context.complexity.value,
                "sensitivity": context.sensitivity.value,
                "verification_score": verification.score,
                "evidence_status": verification.evidence_status,
                "contradictions": context.contradictions,
                "hypotheses": [
                    item.model_dump(mode="json")
                    for item in context.hypotheses
                ],
            },
            constraints=context.constraints,
            evidence=[
                {
                    "type": "memory",
                    "content": item.content[:400],
                    "score": round(item.score, 3),
                    "reliability": item.reliability,
                }
                for item in context.memories[:8]
            ],
            memories=[
                item.content[:300]
                for item in context.memories[:8]
            ],
            options=[
                assignment.system_id
                for assignment in plan.assignments
            ],
            assumptions=plan.assumptions,
            risks=plan.risks,
            confidence=confidence,
            certainty_band=ConfidenceEngine.certainty_band(
                confidence
            ),
            selected_action=CognitiveEngine._extract_action(
                response
            ),
            alternatives_rejected=[
                "Commit immediately without validating evidence.",
                "Treat relevant memory as authoritative fact.",
            ],
            expected_outcome=plan.expected_outcome,
            horizon_checks=plan.horizon_checks,
        )

    @staticmethod
    def _extract_action(response: str) -> str:
        patterns = (
            r"(?i)(?:recommendation|recommended action|next action|action)\s*[:\-]\s*(.+)",
            r"(?i)\bnext\s*[:\-]\s*(.+)",
        )
        for pattern in patterns:
            match = re.search(pattern, response)
            if match:
                return match.group(1).strip()[:1000]
        return next(
            (
                line.strip()
                for line in response.splitlines()
                if line.strip()
            ),
            response.strip(),
        )[:1000]
