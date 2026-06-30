# PAMASMMA v2.1 Architecture Guide

## System Overview Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     PAMASMMA v2.1 System                         │
└─────────────────────────────────────────────────────────────────┘

                        ┌──────────────┐
                        │   Clients    │
                        └──────┬───────┘
                               │
                    ┌──────────▼───────────┐
                    │  Orchestrator API    │
                    │  (Port 3000)         │
                    └──────────┬───────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        │                      │                      │
    ┌───▼────┐          ┌──────▼──────┐        ┌─────▼──────┐
    │ Content │          │ Marketing   │        │ Tool Gate- │
    │ Agent   │          │ Intel       │        │ way        │
    └────┬────┘          └──────┬──────┘        └─────┬──────┘
         │                      │                     │
         └──────────────┬───────┴─────────────────────┘
                        │
                   ┌────▼─────┐
                   │ Event Bus │ (Kafka)
                   └────┬─────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
    ┌───▼──────┐   ┌────▼────┐    ┌────▼────┐
    │ Memory   │   │ Mali    │    │Personality
    │ Core     │   │ Engine  │    │Engine
    └──────────┘   └─────────┘    └────┬────┘
                                        │
                                   ┌────▼────┐
                                   │Self-    │
                                   │Healing  │
                                   └─────────┘
```

---

## Component Architecture

### 1. Orchestrator Service
**Role**: Central task coordinator and router

```typescript
OrchestratorAppService
├── TaskCreator (Domain)
│   └── Creates unique task IDs, timestamps
├── TaskRouter (Domain)
│   └── Routes tasks to appropriate agents
├── MemoryManager (Injected)
│   └── Persists episodic records
└── IEventBus (Injected)
    └── Publishes task.created events
```

**Flow**:
```
POST /api/task
  → TaskCreator.create()
    → MemoryManager.writeMemory()
    → EventBus.emit(task.created)
    → Return task_id
```

---

### 2. Memory Core
**Role**: Episodic & semantic memory with tenant isolation

```typescript
MemoryManager
├── ShortTermMemory (LRU cache)
│   └── Fast access, limited size
├── LongTermMemory (Persistent)
│   ├── EpisodicStore (Map<tenant_id, Map<id, record>>)
│   └── SemanticStore (Map<tenant_id, Map<id, fact>>)
└── MemoryAccessLayer (Tenant-scoped)
    ├── getEpisodic(taskId)
    └── getSemantic(key)
```

**Access Control**:
```
writeMemory() requires context.source === 'domain'
├── Only domain services can write
├── All writes versioned with timestamp
└── Scoped to tenant_id
```

---

### 3. Content Agent
**Role**: Generate branded content with memory integration

```typescript
ContentAgentAppService
├── ContentGenerator (Domain)
│   ├── generate(prompt: string)
│   └── generateCaption(topic: string)
└── MemoryManager (Injected)
    └── Stores generated content as episodic records
```

**Content Pipeline**:
```
generateContent(tenantId, taskId, prompt)
  → ContentGenerator.generate(prompt)
  → MemoryManager.writeMemory(
      { type: 'episodic', data: { content } }
    )
  → Return content
```

---

### 4. Tool Gateway
**Role**: Secure MCP tool execution with injection detection

```typescript
ToolExecutionService
├── ToolRegistry (Domain)
│   └── Manages MCP tool definitions
├── InjectionDetector (Domain)
│   └── Scans for prompt injection patterns
├── IMaliService (Injected)
│   └── Gets Mali risk verdict
├── IMCPClient (Injected)
│   └── Calls actual MCP servers
└── IEventBus (Injected)
    └── Publishes tool.mcp.called events
```

**Security Layers**:
```
execute(toolName, inputs)
  ① InjectionDetector.scan(inputs)
      → REJECT if injection detected
  ② tool.maliRequired?
      → Get IMaliService.evaluate()
      → REJECT if verdict === 'reject'
  ③ IMCPClient.call(server, tool, inputs)
      → Return result or error
```

---

### 5. Mali Engine
**Role**: Adversarial simulation (Red/Blue/Grey teams)

```typescript
AdversarialSimulator
├── MaliRed (Attack vectors)
│   ├── simulateUserMisuse()
│   ├── simulateMarketAttack()
│   └── simulatePlatformRisk()
├── MaliBlue (Defense)
│   └── detectVulnerabilities()
└── MaliGrey (Liability)
    └── assessLiability()
```

**Risk Assessment**:
```
assess(decision)
  redScore = misuse + market + platform
  blueScore = vulnerabilities
  greyScore = liability
  totalScore = (red + blue + grey) / 3
  
  if totalScore > 0.7 → 'reject'
  if totalScore > 0.4 → 'revise'
  else → 'approve'
```

---

### 6. Personality Engine
**Role**: Identity coherence and drift detection

```typescript
PersonalityService
├── IdentityCoherenceEngine (Domain)
│   └── checkDrift(baseline, current)
│       → DriftReport { warning, driftScore, factors }
├── MemoryManager (Injected)
│   └── Retrieves baseline from memory
├── SelfHealingOrchestrator (Injected)
│   └── Triggers remediation if drift > threshold
└── IEventBus (Injected)
    └── Publishes agent.drift.detected events
```

**Drift Detection**:
```
assessCurrentBehavior(tenantId, agentId, currentVector)
  → Get baseline from memory
  → Calculate drift = |baseline[0] - current[0]|
  → if drift > 0.3: warning = true
  → if warning: SelfHealing.handleDrift()
```

---

### 7. Self-Healing Orchestrator
**Role**: Auto-remediation of agent drift

```typescript
SelfHealingOrchestrator
├── AgentVersionManager
│   ├── storeVersion(agentId, version)
│   └── getStableVersion(agentId)
└── IEventBus (Injected)
    └── Emits agent.drift.detected events

Agent rollback strategy:
  1. Store all agent versions with promptHash
  2. On drift detection, retrieve stable version
  3. Emit event for K8s to update deployment
  4. Log rollback action
```

---

### 8. Marketing Intelligence
**Role**: Observational learning with signal recording

```typescript
MarketingIntelService
├── ObservationalLearning (Domain)
│   └── recordSignal(tenantId, taskId, signal)
└── MemoryManager (Injected)
    └── Stores signals as semantic facts
```

**Signal Flow**:
```
updateMarketingSignals(tenantId, taskId, signals)
  → for each signal
    → ObservationalLearning.recordSignal()
    → MemoryManager.writeMemory(
        { type: 'semantic', data: signal }
      )
```

---

## Event Flow

### Event Catalog

```
task.created
  ├── source: Orchestrator
  ├── trigger: POST /api/task
  └── subscribers: [ContentAgent, ToolGateway]

task.processed
  ├── source: ContentAgent
  ├── fields: agent, output, confidence_score
  └── subscribers: [Orchestrator]

tool.mcp.called
  ├── source: ToolGateway
  ├── fields: mcp_server, tool_name, status, mali_verdict
  └── subscribers: [Metrics]

mali.risk.assessed
  ├── source: MaliEngine
  ├── fields: risk_score, failure_modes, recommendation
  └── subscribers: [ToolGateway]

agent.drift.detected
  ├── source: PersonalityEngine
  ├── fields: agent_id, drift_score
  └── subscribers: [SelfHealing]

memory.updated
  ├── source: MemoryCore
  ├── fields: store_type, operation
  └── subscribers: [Audit]
```

---

## Dependency Injection Pattern

### Composition Root
```typescript
// packages/orchestrator/src/index.ts

const bus = new KafkaProducer(); // implements IEventBus
const memory = new MemoryManager();

const service = new OrchestratorAppService(
  new TaskCreator(),
  new TaskRouter(),
  memory,
  bus // injected interface, not implementation
);

// Benefits:
// ✓ Testable (mock bus in tests)
// ✓ Loosely coupled
// ✓ Can swap implementations
```

### Testing Pattern
```typescript
class MockEventBus implements IEventBus {
  events: SystemEvent[] = [];
  
  async emit(event: SystemEvent) {
    this.events.push(event);
  }
  
  subscribe() {}
}

// In tests:
const mockBus = new MockEventBus();
const service = new OrchestratorAppService(
  new TaskCreator(),
  new TaskRouter(),
  new MemoryManager(),
  mockBus
);

await service.createAndRouteTask('t1', 'content', {});
expect(mockBus.events[0].type).toBe('task.created');
```

---

## Data Isolation & Multi-Tenancy

### Tenant Scoping
```
All operations scoped by tenant_id:

Memory:
  episodicStore: Map<tenant_id, Map<id, record>>
  semanticStore: Map<tenant_id, Map<id, fact>>

Events:
  Every event has tenant_id field
  
Access Layers:
  MemoryAccessLayer(tenantId)
    → only sees that tenant's data
```

---

## Error Handling

### Result Type Pattern
```typescript
type Result<T, E = AppError> = Success<T> | Failure<E>

// ✓ No exceptions thrown
// ✓ Errors as values
// ✓ Composable

const result = execute(toolName, inputs);
if (result.ok) {
  console.log(result.value);
} else {
  console.error(result.error.code);
}
```

---

## Scaling Considerations

### Horizontal Scaling
```
Stateless services (Orchestrator, ContentAgent):
  → Can run multiple replicas
  → Use LoadBalancer for distribution
  → Kafka ensures event ordering per partition

Stateful services (Memory):
  → Currently in-process
  → Consider external store (Redis) for scale
  → Use cache invalidation strategy
```

### Vertical Scaling
```
Memory limits per pod:
  Orchestrator: 512Mi
  ContentAgent: 512Mi
  ToolGateway: 256Mi
  
Scale up if:
  - Frequent OOMKilled events
  - High GC pause times
  - Slow task processing
```

---

## Security Model

### Defense Layers

```
Layer 1: Injection Detection
  └─ ToolGateway.InjectionDetector
     └─ Scans all inputs before MCP call

Layer 2: Mali Risk Assessment
  └─ MaliEngine.AdversarialSimulator
     └─ Red/Blue/Grey team evaluation

Layer 3: Memory Access Control
  └─ MemoryManager enforces source === 'domain'
     └─ Only domain services can write

Layer 4: Event Validation
  └─ SchemaValidator on all events
     └─ Prevents malformed events from propagating

Layer 5: Tenant Isolation
  └─ All operations scoped by tenant_id
     └─ No cross-tenant data leakage
```

---

## Performance Optimizations

### Caching
```
ShortTermMemory (LRU):
  - Max 1000 entries
  - O(1) lookup
  - Automatic eviction

Long-term queries:
  - Consider Redis caching layer
  - Cache invalidation on write
```

### Batching
```
Events:
  - Batch writes to Kafka
  - Default: 1024 events or 10s timeout

Memory:
  - Batch episodic updates
  - Semantic facts individually indexed
```

---

## Monitoring & Observability

### Key Metrics

```
Business:
  - tasks_created_total
  - tasks_processed_total
  - mali_blocks_total
  - agent_drift_warnings_total

Performance:
  - http_request_duration_seconds
  - memory_usage_bytes
  - kafka_lag
  - event_bus_latency

System:
  - pod_cpu_usage
  - pod_memory_usage
  - disk_io_ops
  - network_io_bytes
```

### Logging

```
Levels:
  ERROR: Failures, exceptions
  WARN:  Drift detected, Mali blocks
  INFO:  Task created, event emitted
  DEBUG: Memory writes, cache hits

Example:
  [INFO] Task created: task_id=abc, tenant_id=t1, type=content
  [WARN] Agent drift detected: agent_id=content-agent-1, score=0.45
  [ERROR] Injection blocked: pattern=system_prompt, input_hash=xyz
```

---

## Deployment Patterns

### Blue-Green Deployment
```
Version 2.0 (Blue):
  - Running in prod
  - Receiving traffic

Version 2.1 (Green):
  - Deployed separately
  - Zero traffic initially

Switch:
  1. Deploy v2.1
  2. Run smoke tests
  3. Switch LoadBalancer to v2.1
  4. Keep v2.0 running for rollback
```

### Rolling Deployment
```
3 replicas of Orchestrator:

1. Deploy new version to 1 pod
   → Monitor health for 5 min
2. Deploy to 2nd pod
   → Monitor health for 5 min
3. Deploy to 3rd pod
   → Complete

Rollback: Revert image in deployment
```

---

## Future Enhancements

```
Phase 2.2:
  □ External memory store (Redis/PostgreSQL)
  □ Distributed tracing (Jaeger)
  □ Advanced metrics (Prometheus operators)
  □ API authentication (OAuth2/OIDC)

Phase 2.3:
  □ ML-based anomaly detection
  □ Advanced Mali simulation
  □ Multi-region deployment
  □ Disaster recovery automation
```

---

## Troubleshooting Guide

| Issue | Root Cause | Solution |
|-------|-----------|----------|
| High memory | Memory leak in STM | Increase LRU max_size or implement eviction |
| Slow events | Kafka lag | Add more partitions or consumers |
| High latency | Contention on locks | Use async I/O, consider read replicas |
| Frequent OOMKilled | Insufficient memory requests | Increase pod memory limits |
| Event loss | Service crash before Kafka ACK | Enable persistence, add retries |
| Cross-tenant leak | Improper scoping | Audit all memory access code |

