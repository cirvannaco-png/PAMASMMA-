# Experimental — Not Production Code

This directory contains subsystems that are **not yet integrated** into the main
PAMASMMA platform. They are preserved here for continuity and future development,
but they are **not** built, tested, or wired into any running service.

Do not reference these packages from production code until they have been:
1. Given a `package.json` + `tsconfig.json`
2. Added to the root `package.json` workspaces array
3. Covered by tests
4. Reviewed and approved for integration

---

## packages-ai/

> Source: formerly `packages/ai/`

TypeScript explorations covering AI evolution, governance, kernel-fusion, memory
management, causal reasoning, and tool orchestration. Contains interesting
architecture ideas but no runnable logic.

**State:** Scaffolding only. Not integrated into any workflow.

---

## packages-kernel/

> Source: formerly `packages/kernel/`

Lower-level kernel subsystem: event-bus, event-kernel, hardening, memory-core
variant, scheduler, security, and state-engine. Partially overlaps with the live
`packages/memory-core` and `packages/orchestrator` packages.

**State:** Scaffolding only. Assess for merge vs. duplication before integrating.

---

## python/

> Source: formerly `pamasmma-prime/`

Python subsystem covering causal reasoning, calibration, and stability loop.
Has no `requirements.txt` or `pyproject.toml` and is not referenced anywhere in
the Node.js service layer.

**State:** Proof of concept. Needs an API boundary (REST or gRPC) + Docker stage
before it can be wired into the compose/K8s stack.
