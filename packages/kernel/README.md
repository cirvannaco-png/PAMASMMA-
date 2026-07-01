# PAMASMMA Kernel

## Overview
The Kernel is the lowest-level execution core of the PAMASMMA operating system. It is responsible for controlling runtime behavior, orchestrating events, scheduling execution, and maintaining system state integrity.

## Role in Architecture
The Kernel sits above Infrastructure and below Runtime Services.

Flow:
Infrastructure → Kernel → Runtime → Platform Services → AI Engines → Applications

## Core Responsibilities
- Event ingestion and routing
- Execution scheduling
- State coordination
- Service orchestration (via Service Registry)
- Plugin execution control
- Memory interaction mediation

## Design Principles
- Deterministic execution layer
- No business logic
- No AI logic
- No direct application logic
- Fully event-driven
- Strict separation from higher layers

## Subsystems (Phase 2.1 Targets)
- event-kernel/
- scheduler/
- memory-core/
- service-orchestrator/
- plugin-runtime/
- state-engine/

## Status
Phase 2.1 initialization complete. Submodules will be incrementally implemented under Governance supervision.
