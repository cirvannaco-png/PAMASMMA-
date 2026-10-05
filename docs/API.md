# PAMASMMA v4.2 — API Reference

Base path: /api/v1

Authenticated cognitive routes use:

~~~text
Authorization: Bearer <access_token>
~~~

## Cognitive invocation

### GET /cognitive/systems

Returns the ten governed cognitive systems.

### POST /cognitive/invoke

Request:

~~~json
{
  "system_id": "S1",
  "messages": [
    { "role": "user", "content": "What should I prioritize this quarter?" }
  ],
  "stream": false
}
~~~

Non-stream response includes:

~~~json
{
  "system_id": "S1",
  "system_name": "Executive Operations",
  "response": "...",
  "cognition": {
    "intent": "decision",
    "complexity": "strategic",
    "sensitivity": "standard",
    "memory_count": 5,
    "contradiction_count": 0,
    "routed_systems": ["S1", "S10", "S2"],
    "provider": "kernel",
    "confidence": 0.71,
    "evidence_status": "structural_only",
    "decision_id": "uuid"
  },
  "decision": {
    "id": "uuid",
    "objective": "...",
    "confidence": 0.71,
    "certainty_band": "moderate-high",
    "selected_action": "...",
    "expected_outcome": "...",
    "horizon_checks": {
      "30d": "...",
      "90d": "...",
      "1y": "...",
      "3y": "...",
      "10y": "..."
    }
  }
}
~~~

stream=true preserves the SSE contract. The engine verifies the complete response before emission.

## Decision records

### GET /cognitive/decisions

Returns recent user-owned decision records.

Query:

- limit: 1–200, default 50.

### GET /cognitive/decisions/{decision_id}

Returns one user-owned decision. Cross-user access returns 404.

## Outcome learning

### POST /cognitive/decisions/{decision_id}/outcome

Request:

~~~json
{
  "observed_outcome": "The validation passed and deployment stability improved.",
  "success_score": 0.9,
  "failure_domain": "unknown",
  "lesson": ""
}
~~~

When failure_domain is unknown, PAMASMMA derives a conservative failure domain from the observed outcome.

Prediction error is:

~~~text
abs(success_score - decision.confidence)
~~~

The learning engine stores both an outcome memory and a procedural lesson.

### GET /cognitive/outcomes

Returns recent learned outcomes for the authenticated user.

## Invocation audit

### GET /cognitive/action-log

Returns invocation telemetry.

Query:

- system_id: optional S1–S10 filter
- limit: 1–200

## Governed overrides

### POST /cognitive/override

Queues a behavioral override for governed processing.

## Realtime events

### GET /events/stream?token=<access_token>

Authenticated SSE stream.

Event types:

~~~text
cognitive_invocation
cognitive_outcome
override_queue
scheduler_event
heartbeat
~~~

User-scoped events are filtered server-side.

## Health

### GET /health

Basic service health.

### GET /health/ready

Readiness for durable dependencies; returns HTTP 503 when required persistent dependencies are unavailable.

## Authentication

Authentication remains under /auth/* and supports TOTP, WebAuthn, JWT session handling and logout.
