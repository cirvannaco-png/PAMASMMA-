# PAMASMMA v2.1

**Platform for Autonomous Multi-Agent Social Media Marketing Architecture**

A production-grade, multi-tenant AI agent system for governed social media content generation, adversarial risk assessment, and self-healing agent management.

---

## Overview

PAMASMMA orchestrates a fleet of specialised AI agents, each responsible for a distinct capability, coordinated through an event-driven architecture. Every content decision passes through an adversarial risk gate (Mali) before execution, and all agents are monitored for personality drift with automatic self-healing.

```
Clients
  └── Orchestrator API (port 3000)
        ├── Content Agent      — generates branded content and captions
        ├── Marketing Intel    — observational learning, trend analysis
        ├── Tool Gateway       — secure MCP tool execution with injection detection
        ├── Mali Engine        — Red / Blue / Grey adversarial risk scoring
        ├── Personality Engine — identity coherence and drift monitoring
        ├── Relationship Graph — tenant relationship tracking
        └── Self-Healing       — automatic rollback and agent remediation
              │
           Event Bus (Kafka)
              ├── Memory Core (episodic + semantic, tenant-isolated)
              └── Observability (Prometheus metrics + OpenTelemetry traces)
```

---

## Packages

| Package | Description |
|---|---|
| `@pamasmma/shared` | Shared types, events, Result monad, metrics, resilience, tracing |
| `@pamasmma/memory-core` | Episodic & semantic memory with LRU short-term cache and tenant isolation |
| `@pamasmma/orchestrator` | Central task coordinator — REST API, task routing, task store |
| `@pamasmma/content-agent` | Content generation and caption creation |
| `@pamasmma/tool-gateway` | Secure MCP tool execution with multi-layer injection detection |
| `@pamasmma/mali-engine` | Adversarial simulation: Red (attacks), Blue (defence), Grey (liability) |
| `@pamasmma/personality-engine` | Behaviour drift detection using vector similarity |
| `@pamasmma/marketing-intel` | Trend observation and marketing intelligence |
| `@pamasmma/relationship-graph` | Graph-based relationship model |
| `@pamasmma/self-healing` | Agent version management and automated remediation |

---

## Getting Started

### Prerequisites

- Node.js ≥ 20
- Yarn

### Install

```bash
yarn install
```

### Run in development

```bash
yarn dev
```

The Orchestrator API starts on port 3000 (configurable via `PORT`).

### Build

```bash
yarn build
```

### Test

```bash
yarn test
```

Run with coverage:

```bash
yarn test --coverage
```

### Lint

```bash
yarn lint
```

---

## API Reference

All routes are mounted at `/api`.

### Health

```
GET /api/health
```

Response:
```json
{ "status": "ok", "service": "orchestrator", "ts": "2025-01-01T00:00:00.000Z" }
```

### Tasks

#### Create a task
```
POST /api/task
Content-Type: application/json

{
  "tenant_id": "my-tenant",
  "type": "content",        // content | marketing | social | email
  "input": { "prompt": "Write a post about coffee" }
}
```

Response `201`:
```json
{ "task_id": "550e8400-e29b-41d4-a716-446655440000" }
```

#### List tasks for a tenant
```
GET /api/tasks?tenant_id=my-tenant
```

Response `200`:
```json
{ "tasks": [...], "count": 3 }
```

#### Get a task
```
GET /api/task/:id?tenant_id=my-tenant
```

#### Update task status
```
PATCH /api/task/:id/status
Content-Type: application/json

{ "tenant_id": "my-tenant", "status": "completed" }
```

Valid statuses: `pending`, `processing`, `completed`, `failed`, `cancelled`

#### Cancel a task
```
DELETE /api/task/:id?tenant_id=my-tenant
```

Response `200`:
```json
{ "cancelled": true, "task_id": "..." }
```

---

## Security

### Injection Detection

The `InjectionDetector` in `@pamasmma/tool-gateway` scans all tool inputs recursively (strings, nested objects, arrays) for:

- Template injection (Jinja2, Handlebars, Twig)
- Server-side injection (PHP, shell command substitution, backticks)
- Script / XSS injection (`<script>`, `javascript:`, inline event handlers)
- LLM prompt injection (`ignore previous instructions`, role-override attempts, system-prompt extraction)
- SQL injection patterns

### Mali Adversarial Gate

Every tool execution with `maliRequired: true` is evaluated by three agents before execution:

| Agent | Checks |
|---|---|
| **MaliRed** | User misuse, market attack, platform policy risk |
| **MaliBlue** | Content vulnerabilities, dark patterns |
| **MaliGrey** | Legal/compliance liability (medical, financial) |

Combined score → `approve` / `revise` / `reject`.

---

## Architecture

See [ARCHITECTURE.md](./ARCHITECTURE.md) for the full component breakdown, sequence diagrams, and ADR index.

---

## Infrastructure

Kubernetes manifests are in `infra/kubernetes/`. Grafana dashboards are in `grafana-dashboards/`.

### Deploying to Kubernetes

```bash
kubectl apply -f infra/kubernetes/namespace.yaml
kubectl apply -f infra/kubernetes/configmap.yaml
kubectl apply -f infra/kubernetes/secrets.yaml
kubectl apply -f infra/kubernetes/services.yaml
kubectl apply -f infra/kubernetes/orchestrator-deployment.yaml
kubectl apply -f infra/kubernetes/content-agent-deployment.yaml
kubectl apply -f infra/kubernetes/tool-gateway-deployment.yaml
kubectl apply -f infra/kubernetes/ingress.yaml
kubectl apply -f infra/kubernetes/autoscaler.yaml
```

See [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md) for full environment setup.

---

## Observability

- **Metrics**: Prometheus-compatible endpoint at `GET /metrics` on each service (via `prom-client`)
- **Tracing**: OpenTelemetry with OTLP exporter (configure `OTEL_EXPORTER_OTLP_ENDPOINT`)
- **Dashboards**: Import JSON files from `grafana-dashboards/` into Grafana

Key metrics:

| Metric | Description |
|---|---|
| `http_request_duration_seconds` | Request latency by service and route |
| `injection_attempts_total` | Total prompt injection attempts blocked |
| `mali_block_total` | Total executions blocked by Mali |
| `agent_drift_warnings_total` | Agent personality drift warnings |

---

## Event Schema

All events extend `BaseEvent`:

```typescript
interface BaseEvent {
  type: string;
  schema_version: number;
  timestamp: string;   // ISO 8601
  tenant_id: string;
  task_id: string;
}
```

Event types: `task.created`, `task.processed`, `task.approved`, `agent.content.generated`, `tool.mcp.called`, `mali.risk.assessed`, `memory.updated`, `agent.drift.detected`

---

## Project Structure

```
packages/
├── shared/            # Shared types, events, utilities
├── memory-core/       # Episodic & semantic memory
├── orchestrator/      # Task coordination API
├── content-agent/     # Content generation
├── tool-gateway/      # Secure MCP execution
├── mali-engine/       # Adversarial risk scoring
├── personality-engine/# Drift detection
├── marketing-intel/   # Marketing intelligence
├── relationship-graph/# Relationship graph
└── self-healing/      # Self-healing & version management
architecture/          # ADRs and PAC constitution
infra/kubernetes/      # K8s manifests
grafana-dashboards/    # Grafana dashboard JSON
pamasmma-prime/        # Python: causal reasoning & stability
```

---

## License

See [LICENSE](./LICENSE).
