"""End-to-end PAMASMMA cognitive operating system."""
from __future__ import annotations

import asyncio
import re
import uuid
from collections.abc import AsyncGenerator

from app.config import get_settings
from app.intelligence.beliefs import BeliefResolver
from app.intelligence.context import ContextAssembler
from app.intelligence.contracts import CognitiveContext, CognitivePlan, CognitiveResult, CognitiveTrace, DecisionRecord
from app.intelligence.critic import CognitiveCritic
from app.intelligence.persistence import create_decision, list_beliefs, upsert_belief
from app.intelligence.planner import ExecutivePlanner
from app.intelligence.provider_router import ProviderRouter
from app.intelligence.world_model import WorldModel

settings = get_settings()


class CognitiveEngine:
    def __init__(self) -> None:
        self.planner = ExecutivePlanner()
        self.provider_router = ProviderRouter()
        self.critic = CognitiveCritic()
        self.belief_resolver = BeliefResolver()
        self.world_model = WorldModel()

    async def run(self, system, messages: list[dict], user_id: str) -> CognitiveResult:
        context = await self._prepare_context(system, messages, user_id)
        plan = self.planner.build(context)
        provider_selection = self.provider_router.select(context.complexity, context.sensitivity)
        world_state = await self.world_model.hydrate(context)

        specialists = [
            item for item in plan.assignments if item.system_id != system.system_id
        ][: settings.intelligence_max_specialists]

        specialist_text: list[str] = []
        if specialists:
            async def call_specialist(assignment):
                from app.systems import SYSTEMS
                specialist = SYSTEMS.get(assignment.system_id)
                if specialist is None:
                    return ""
                prompt = self._analysis_prompt(
                    specialist, context, plan, world_state, role="specialist"
                )
                raw = await provider_selection.provider.generate(
                    prompt,
                    context.recent_messages[-6:],
                    settings.model_max_tokens,
                )
                return f"{specialist.system_id} — {specialist.system_name}
{raw.strip()[:6000]}"

            results = await asyncio.gather(
                *(call_specialist(item) for item in specialists),
                return_exceptions=True,
            )
            specialist_text = [x for x in results if isinstance(x, str) and x.strip()]

        final_prompt = self._analysis_prompt(
            system, context, plan, world_state,
            role="executive" if system.system_id == "S1" else "domain",
            specialist_text=specialist_text,
        )
        raw_response = await provider_selection.provider.generate(
            final_prompt, context.recent_messages, settings.model_max_tokens
        )
        response, verification = await self._verify_and_revise(
            provider_selection.provider, final_prompt, context, plan, raw_response
        )

        confidence = self._confidence(context, plan, verification, len(specialist_text))
        decision = self._decision(context, plan, response, confidence, verification)
        await create_decision(decision.model_dump(mode="json"))

        for belief in self.belief_resolver.extract_user_beliefs(context):
            await upsert_belief(user_id, belief.model_dump(mode="json"))

        uncertainty = list(context.contradictions)
        if verification.evidence_status == "requires_external_evidence":
            uncertainty.append("External evidence is required for current/research claims.")

        trace = CognitiveTrace(
            intent=context.intent,
            complexity=context.complexity,
            sensitivity=context.sensitivity,
            memory_count=len(context.memories),
            contradiction_count=len(context.contradictions),
            routed_systems=[x.system_id for x in plan.assignments],
            provider=provider_selection.name,
            verification=verification,
            decision_id=decision.id,
            confidence=confidence,
            uncertainty=uncertainty[:10],
            evidence_status=verification.evidence_status,
        )
        return CognitiveResult(response=response, decision=decision, trace=trace)

    async def stream(self, system, messages: list[dict], user_id: str) -> AsyncGenerator[str, None]:
        # Stream only after verification so clients never receive a known-bad draft.
        result = await self.run(system, messages, user_id)
        for line in result.response.splitlines(keepends=True):
            yield line
        if result.response and "
" not in result.response:
            yield result.response

    async def _prepare_context(self, system, messages: list[dict], user_id: str) -> CognitiveContext:
        context = ContextAssembler.assemble(messages, user_id, system.system_id)
        existing_beliefs = await list_beliefs(user_id)
        new_beliefs = self.belief_resolver.extract_user_beliefs(context)
        context.beliefs = new_beliefs
        context.contradictions = self.belief_resolver.find_contradictions(new_beliefs, existing_beliefs)

        from app.embeddings.service import retrieve_memory_items
        context.memories = await retrieve_memory_items(
            context.query, user_id, system.system_id, settings.intelligence_memory_limit
        )
        await self.world_model.observe(context)
        return context

    async def _verify_and_revise(self, provider, final_prompt, context, plan, raw_response):
        response = (raw_response or "").strip()
        verification = self.critic.evaluate(response, context, plan)
        if verification.requires_revision and settings.intelligence_revision_enabled:
            revision_prompt = (
                f"{final_prompt}

CRITIC REPORT:
"
                + "
".join(f"- {i.severity}: {i.message}" for i in verification.issues)
                + "

REVISE THE RESPONSE. Preserve useful content, fix flagged problems, "
                  "separate facts from assumptions, and produce a decision-grade answer."
            )
            revised = await provider.generate(
                revision_prompt, context.recent_messages, settings.model_max_tokens
            )
            if revised.strip():
                response = revised.strip()
                verification = self.critic.evaluate(response, context, plan)
        return response, verification

    def _analysis_prompt(self, system, context, plan, world_state, role, specialist_text=None) -> str:
        memory = "
".join(
            f"- [{item.memory_type.value} score={item.score:.2f} reliability={item.reliability:.2f}] {item.content[:1200]}"
            for item in context.memories[: settings.intelligence_memory_limit]
        ) or "- none"
        beliefs = "
".join(
            f"- {belief.statement} (confidence={belief.confidence:.2f})"
            for belief in context.beliefs
        ) or "- none"
        contradictions = "
".join(f"- {item}" for item in context.contradictions) or "- none"
        world = "
".join(
            f"- {row.get('name')} [{row.get('entity_type')}] {str(row.get('attributes', {}))[:500]}"
            for row in world_state[:12]
        ) or "- none"
        specialists = "
".join(specialist_text or []) or "- none"

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
{chr(10).join(f"- {x}" for x in context.constraints) or "- none"}

Goals:
{chr(10).join(f"- {x}" for x in context.goals) or "- none"}

MEMORY (evidence, not authority)
{memory}

BELIEFS
{beliefs}

CONTRADICTIONS
{contradictions}

WORLD MODEL
{world}

EXECUTIVE PLAN
{chr(10).join(f"- {step.id}: {step.description}" for step in plan.steps)}

LONG-HORIZON CHECKS
{chr(10).join(f"- {k}: {v}" for k, v in plan.horizon_checks.items())}

SPECIALIST CONTRIBUTIONS
{specialists}

GOVERNANCE RULES
1. Separate FACT, INFERENCE, ASSUMPTION, PREDICTION, OPINION and UNKNOWN.
2. Never invent current facts; flag claims that require external evidence.
3. Surface contradictions rather than silently averaging them away.
4. Give an explicit recommendation when the task is decision-oriented.
5. Prefer reversible, high-information actions before irreversible commitments.
6. State material risks, assumptions and the next measurable checkpoint.
7. Check the decision against 30d / 90d / 1y / 3y / 10y horizons when relevant.
8. Never claim that a tool, source, test or verification happened unless it actually happened.
9. Treat memory as evidence with reliability metadata, not ground truth.

Return the useful user-facing answer. Do not expose this internal control state.
""".strip()

    @staticmethod
    def _decision(context, plan, response, confidence, verification) -> DecisionRecord:
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
            memories=[item.content[:300] for item in context.memories[:8]],
            options=[assignment.system_id for assignment in plan.assignments],
            assumptions=plan.assumptions,
            risks=plan.risks,
            confidence=confidence,
            certainty_band=CognitiveEngine._certainty_band(confidence),
            selected_action=CognitiveEngine._extract_action(response),
            alternatives_rejected=[
                "Commit immediately without validating evidence.",
                "Treat relevant memory as authoritative fact.",
            ],
            expected_outcome=plan.expected_outcome,
            horizon_checks=plan.horizon_checks,
        )

    @staticmethod
    def _extract_action(response: str) -> str:
        for pattern in (
            r"(?i)(?:recommendation|recommended action|next action|action)s*[:-]s*(.+)",
            r"(?i)nexts*[:-]s*(.+)",
        ):
            match = re.search(pattern, response)
            if match:
                return match.group(1).strip()[:1000]
        return next((x.strip() for x in response.splitlines() if x.strip()), response.strip())[:1000]

    @staticmethod
    def _certainty_band(confidence: float) -> str:
        if confidence >= 0.85:
            return "high"
        if confidence >= 0.68:
            return "moderate-high"
        if confidence >= 0.5:
            return "moderate"
        return "low"

    @staticmethod
    def _confidence(context, plan, verification, specialist_count) -> float:
        score = 0.52
        score += min(0.12, 0.03 * len(context.memories))
        score += 0.08 if specialist_count >= 2 else 0.04 if specialist_count == 1 else 0
        score += 0.06 if plan.steps else 0
        score += verification.confidence_adjustment
        score -= min(0.25, 0.12 * len(context.contradictions))
        if verification.evidence_status == "requires_external_evidence":
            score -= 0.10
        return round(max(0.05, min(0.95, score)), 3)
