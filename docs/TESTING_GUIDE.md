# PAMASMMA Comprehensive Testing Guide v2.1

## Table of Contents
1. [Testing Architecture](#testing-architecture)
2. [Unit Testing](#unit-testing)
3. [Integration Testing](#integration-testing)
4. [End-to-End Testing](#end-to-end-testing)
5. [Performance Testing](#performance-testing)
6. [Security Testing](#security-testing)
7. [Observability & Debugging](#observability--debugging)
8. [CI/CD Pipeline](#cicd-pipeline)

---

## Testing Architecture

### Overview
PAMASMMA uses a **layered testing strategy** with:
- ✅ **Unit Tests**: Domain logic, utilities, pure functions
- ✅ **Integration Tests**: Package interactions, event bus, memory access
- ✅ **E2E Tests**: Full workflow from API to database
- ✅ **Performance Tests**: Latency, throughput, resource usage
- ✅ **Security Tests**: Injection detection, authorization, Mali verification
- ✅ **Observability**: OpenTelemetry traces, Prometheus metrics, structured logging

### Test Framework Stack
```json
{
  "jest": "^29.0.0",
  "ts-jest": "^29.0.0",
  "supertest": "^6.3.0",
  "@types/jest": "^29.0.0"
}
```

---

## Unit Testing

### 1. Shared Package Tests

#### Test: `packages/shared/__tests__/result.test.ts`
```typescript
import { ok, fail, AppError } from '../src/result';

describe('Result Type', () => {
  test('ok() creates Success with value', () => {
    const result = ok(42);
    expect(result.ok).toBe(true);
    expect(result.value).toBe(42);
  });

  test('fail() creates Failure with AppError', () => {
    const error = new AppError('Test error', 'TEST_CODE', 400);
    const result = fail(error);
    expect(result.ok).toBe(false);
    expect(result.error.code).toBe('TEST_CODE');
  });

  test('Result type guards work correctly', () => {
    const success = ok('value');
    const failure = fail(new AppError('err', 'ERR'));

    if (success.ok) {
      expect(typeof success.value).toBe('string');
    }

    if (!failure.ok) {
      expect(failure.error.code).toBe('ERR');
    }
  });
});
```

#### Test: `packages/shared/__tests__/schemaValidator.test.ts`
```typescript
import { validateEvent } from '../src/schemaValidator';
import { TaskCreatedEvent } from '../src/events';

describe('Schema Validator', () => {
  test('validates TaskCreatedEvent', () => {
    const validEvent: TaskCreatedEvent = {
      type: 'task.created',
      schema_version: 1,
      timestamp: new Date().toISOString(),
      tenant_id: 't1',
      task_id: 'task-1',
      task_type: 'content',
      input: { title: 'Test' },
    };

    expect(validateEvent(validEvent)).toBe(true);
  });

  test('rejects events with missing required fields', () => {
    const invalidEvent = {
      type: 'task.created',
      timestamp: new Date().toISOString(),
      // missing: schema_version, tenant_id, task_id, task_type, input
    };

    expect(validateEvent(invalidEvent as any)).toBe(false);
  });
});
```

#### Test: `packages/shared/__tests__/resilience.test.ts`
```typescript
import { defaultRetryPolicy, defaultTimeoutPolicy } from '../src/resilience';

describe('Resilience Patterns', () => {
  test('retry policy retries on transient errors', async () => {
    let attempts = 0;
    const fn = async () => {
      attempts++;
      if (attempts < 3) throw new Error('Transient');
      return 'success';
    };

    const result = await defaultRetryPolicy.execute(fn);
    expect(result).toBe('success');
    expect(attempts).toBe(3);
  });

  test('timeout policy cancels long-running operations', async () => {
    const slowFn = async () => {
      await new Promise((r) => setTimeout(r, 10000));
    };

    await expect(defaultTimeoutPolicy.execute(slowFn)).rejects.toThrow();
  });
});
```

### 2. Memory-Core Package Tests

#### Test: `packages/memory-core/__tests__/MemoryManager.test.ts`
```typescript
import { MemoryManager } from '../src/MemoryManager';
import { MemoryEntry } from '../src/types';

describe('MemoryManager', () => {
  let manager: MemoryManager;

  beforeEach(() => {
    manager = new MemoryManager();
  });

  test('writes episodic memory with tenant isolation', async () => {
    const entry: MemoryEntry = {
      id: 'ep-1',
      type: 'episodic',
      data: { event: 'task_completed', result: 'success' },
      timestamp: new Date().toISOString(),
    };

    await manager.writeMemory(entry, {
      source: 'domain',
      tenant_id: 't1',
      task_id: 'task-1',
    });

    const layer = manager.createAccessLayer('t1');
    const retrieved = layer.getFromSTM('ep-1');

    expect(retrieved).toBeDefined();
    expect(retrieved?.version).toBeDefined();
    expect(retrieved?.tenant_id).toBe('t1');
  });

  test('creates separate access layers per tenant', async () => {
    const entry1: MemoryEntry = {
      id: 'data-t1',
      type: 'semantic',
      data: { secret: 'tenant1' },
      timestamp: new Date().toISOString(),
    };

    await manager.writeMemory(entry1, {
      source: 'domain',
      tenant_id: 't1',
      task_id: 'task-1',
    });

    const layer1 = manager.createAccessLayer('t1');
    const layer2 = manager.createAccessLayer('t2');

    expect(layer1.getFromSTM('data-t1')).toBeDefined();
    expect(layer2.getFromSTM('data-t1')).toBeUndefined();
  });
});
```

### 3. Orchestrator Domain Tests

#### Test: `packages/orchestrator/__tests__/taskManagement.test.ts`
```typescript
import { TaskCreator, TaskRouter } from '../src/domain/taskManagement';

describe('Task Management', () => {
  describe('TaskCreator', () => {
    let creator: TaskCreator;

    beforeEach(() => {
      creator = new TaskCreator();
    });

    test('creates task with unique ID', () => {
      const task1 = creator.create({
        tenant_id: 't1',
        type: 'content',
        input: { title: 'Test' },
      });
      const task2 = creator.create({
        tenant_id: 't1',
        type: 'content',
        input: { title: 'Test' },
      });

      expect(task1.id).not.toBe(task2.id);
      expect(task1.status).toBe('pending');
    });
  });

  describe('TaskRouter', () => {
    let router: TaskRouter;

    beforeEach(() => {
      router = new TaskRouter();
    });

    test('routes tasks to correct agents', () => {
      const contentTask = { type: 'content' } as any;
      const marketingTask = { type: 'marketing' } as any;

      expect(router.route(contentTask)).toBe('content-agent');
      expect(router.route(marketingTask)).toBe('marketing-agent');
    });
  });
});
```

### 4. Tool-Gateway Security Tests

#### Test: `packages/tool-gateway/__tests__/InjectionDetector.test.ts`
```typescript
import { InjectionDetector } from '../src/domain/InjectionDetector';

describe('InjectionDetector', () => {
  let detector: InjectionDetector;

  beforeEach(() => {
    detector = new InjectionDetector();
  });

  test('detects template injection (Jinja)', () => {
    expect(detector.scan('{{ malicious }}')).toBe(true);
  });

  test('detects PHP tags', () => {
    expect(detector.scan('<?php system("ls"); ?>')).toBe(true);
  });

  test('detects backtick code execution', () => {
    expect(detector.scan('`whoami`')).toBe(true);
  });

  test('allows safe input', () => {
    expect(detector.scan('This is safe content')).toBe(false);
  });
});
```

### 5. Mali Engine Tests

#### Test: `packages/mali-engine/__tests__/AdversarialSimulator.test.ts`
```typescript
import { AdversarialSimulator } from '../src/domain/AdversarialSimulator';

describe('Mali Adversarial Simulator', () => {
  let simulator: AdversarialSimulator;

  beforeEach(() => {
    simulator = new AdversarialSimulator();
  });

  describe('Red Team (Attack Scenarios)', () => {
    test('flags promotional spam', () => {
      const result = simulator.evaluate({
        content: 'Get 100% free premium guaranteed!',
      });
      expect(result.verdict).toBe('reject');
      expect(result.risk_score).toBeGreaterThan(0.7);
    });

    test('flags competitor attacks', () => {
      const result = simulator.evaluate({
        content: 'Our competitor X is inferior',
      });
      expect(result.verdict).toMatch(/reject|revise/);
    });
  });

  describe('Blue Team (Defense)', () => {
    test('approves certified claims', () => {
      const result = simulator.evaluate({
        content: 'Our certified product features...',
      });
      expect(result.verdict).toBe('approve');
    });
  });

  describe('Grey Team (Edge Cases)', () => {
    test('flags ambiguous language', () => {
      const result = simulator.evaluate({
        content: 'Possibly might help with supposedly...',
      });
      expect(result.verdict).toMatch(/revise|reject/);
    });
  });
});
```

---

## Integration Testing

### 1. Orchestrator Integration Test

#### Test: `packages/orchestrator/__tests__/orchestratorAppService.test.ts`
```typescript
import { OrchestratorAppService } from '../src/application/orchestratorAppService';
import { TaskCreator, TaskRouter } from '../src/domain/taskManagement';
import { MemoryManager } from '@pamasmma/memory-core';
import { IEventBus } from '@pamasmma/shared';

class MockEventBus implements IEventBus {
  events: any[] = [];
  async emit(event: any) {
    this.events.push(event);
  }
  subscribe() {}
}

describe('OrchestratorAppService Integration', () => {
  let service: OrchestratorAppService;
  let eventBus: MockEventBus;
  let memoryManager: MemoryManager;

  beforeEach(() => {
    eventBus = new MockEventBus();
    memoryManager = new MemoryManager();
    service = new OrchestratorAppService(
      new TaskCreator(),
      new TaskRouter(),
      memoryManager,
      eventBus
    );
  });

  test('creates task, stores in memory, and emits event', async () => {
    const taskId = await service.createAndRouteTask('t1', 'content', {
      title: 'Social post',
    });

    expect(taskId).toBeDefined();
    expect(eventBus.events.length).toBe(1);
    expect(eventBus.events[0].type).toBe('task.created');
    expect(eventBus.events[0].task_id).toBe(taskId);

    // Verify memory write
    const layer = memoryManager.createAccessLayer('t1');
    const stored = layer.getFromSTM(taskId);
    expect(stored).toBeDefined();
  });
});
```

### 2. Tool Execution Integration

#### Test: `packages/tool-gateway/__tests__/ToolExecutionService.test.ts`
```typescript
import { ToolExecutionService } from '../src/application/ToolExecutionService';
import { ToolRegistry } from '../src/domain/ToolRegistry';
import { InjectionDetector } from '../src/domain/InjectionDetector';
import { IMaliService, IMCPClient, IEventBus } from '@pamasmma/shared';

class MockMaliService implements IMaliService {
  verdicts: Record<string, string> = {};
  async evaluate(taskId: string) {
    return (this.verdicts[taskId] || 'approve') as any;
  }
}

class MockMCPClient implements IMCPClient {
  async call(server: string, toolName: string, inputs: unknown) {
    return { status: 'success', result: 'mock execution' };
  }
}

class MockEventBus implements IEventBus {
  events: any[] = [];
  async emit(event: any) {
    this.events.push(event);
  }
  subscribe() {}
}

describe('ToolExecutionService Integration', () => {
  let service: ToolExecutionService;
  let registry: ToolRegistry;
  let maliService: MockMaliService;
  let mcpClient: MockMCPClient;
  let eventBus: MockEventBus;

  beforeEach(() => {
    registry = new ToolRegistry();
    maliService = new MockMaliService();
    mcpClient = new MockMCPClient();
    eventBus = new MockEventBus();
    service = new ToolExecutionService(
      registry,
      new InjectionDetector(),
      maliService,
      mcpClient,
      eventBus
    );
  });

  test('rejects injection before Mali check', async () => {
    const result = await service.execute('test_tool', '{{ injection }}', {
      tenant_id: 't1',
      task_id: 'task1',
      trace_id: 'trace1',
    });

    expect(result.ok).toBe(false);
    expect(result.error.code).toBe('INJECTION_BLOCKED');
    expect(eventBus.events[0].status).toBe('rejected');
  });

  test('respects Mali verdict', async () => {
    maliService.verdicts['task1'] = 'reject';

    const result = await service.execute('test_tool', { safe: 'input' }, {
      tenant_id: 't1',
      task_id: 'task1',
      trace_id: 'trace1',
    });

    expect(result.ok).toBe(false);
    expect(result.error.code).toBe('MALI_REJECTED');
  });
});
```

### 3. Memory + Personality Integration

#### Test: `packages/personality-engine/__tests__/PersonalityService.test.ts`
```typescript
import { PersonalityService } from '../src/application/PersonalityService';
import { MemoryManager } from '@pamasmma/memory-core';
import { IEventBus } from '@pamasmma/shared';

class MockEventBus implements IEventBus {
  events: any[] = [];
  async emit(event: any) {
    this.events.push(event);
  }
  subscribe() {}
}

describe('PersonalityService + Memory Integration', () => {
  let service: PersonalityService;
  let memoryManager: MemoryManager;
  let eventBus: MockEventBus;

  beforeEach(async () => {
    memoryManager = new MemoryManager();
    eventBus = new MockEventBus();
    service = new PersonalityService(memoryManager, eventBus);

    // Store baseline personality
    await memoryManager.writeMemory(
      {
        type: 'semantic',
        id: 'personality-baseline-agent1',
        data: { vector: { tone: 0.8, creativity: 0.7 } },
        timestamp: new Date().toISOString(),
      },
      { source: 'domain', tenant_id: 't1', task_id: 'setup' }
    );
  });

  test('detects personality drift and emits event', async () => {
    const driftReport = await service.assessCurrentBehavior(
      't1',
      'agent1',
      { tone: 0.2, creativity: 0.8 } // major drift
    );

    expect(driftReport.warning).toBe(true);
    expect(eventBus.events.some((e) => e.type === 'agent.drift.detected')).toBe(
      true
    );
  });
});
```

---

## End-to-End Testing

### 1. Full Request-Response Flow

#### Test: `packages/orchestrator/__tests__/routes.test.ts`
```typescript
import request from 'supertest';
import express from 'express';
import { OrchestratorAppService } from '../src/application/orchestratorAppService';
import { TaskCreator, TaskRouter } from '../src/domain/taskManagement';
import { MemoryManager } from '@pamasmma/memory-core';
import { IEventBus } from '@pamasmma/shared';
import { orchestratorRoutes } from '../src/presentation/routes';

class MockEventBus implements IEventBus {
  events: any[] = [];
  async emit(event: any) {
    this.events.push(event);
  }
  subscribe() {}
}

describe('Orchestrator E2E', () => {
  let app: express.Application;
  let eventBus: MockEventBus;

  beforeEach(() => {
    eventBus = new MockEventBus();
    const service = new OrchestratorAppService(
      new TaskCreator(),
      new TaskRouter(),
      new MemoryManager(),
      eventBus
    );

    app = express();
    app.use(express.json());
    app.use('/api', orchestratorRoutes(service));
  });

  test('POST /api/task returns 200 with task_id', async () => {
    const res = await request(app)
      .post('/api/task')
      .send({
        tenant_id: 'tenant-1',
        type: 'content',
        input: { platform: 'instagram', caption: 'Hello' },
      });

    expect(res.status).toBe(200);
    expect(res.body.task_id).toBeDefined();
  });

  test('event is emitted to bus', async () => {
    await request(app)
      .post('/api/task')
      .send({
        tenant_id: 'tenant-1',
        type: 'marketing',
        input: { campaign: 'summer' },
      });

    expect(eventBus.events.length).toBeGreaterThan(0);
    expect(eventBus.events[0].type).toBe('task.created');
  });
});
```

---

## Performance Testing

### 1. Latency Benchmarks

#### Test: `__tests__/performance/latency.test.ts`
```typescript
import { OrchestratorAppService } from '../../packages/orchestrator/src/application/orchestratorAppService';
import { TaskCreator, TaskRouter } from '../../packages/orchestrator/src/domain/taskManagement';
import { MemoryManager } from '../../packages/memory-core/src';
import { IEventBus } from '../../packages/shared/src';

class DummyEventBus implements IEventBus {
  async emit() {}
  subscribe() {}
}

describe('Performance: Orchestrator', () => {
  let service: OrchestratorAppService;

  beforeEach(() => {
    service = new OrchestratorAppService(
      new TaskCreator(),
      new TaskRouter(),
      new MemoryManager(),
      new DummyEventBus()
    );
  });

  test('creates task in < 10ms', async () => {
    const start = performance.now();
    for (let i = 0; i < 100; i++) {
      await service.createAndRouteTask('t1', 'content', { i });
    }
    const elapsed = performance.now() - start;
    const avgLatency = elapsed / 100;

    expect(avgLatency).toBeLessThan(10);
  });
});
```

### 2. Throughput Testing

#### Test: `__tests__/performance/throughput.test.ts`
```typescript
import { AdversarialSimulator } from '../../packages/mali-engine/src/domain/AdversarialSimulator';

describe('Performance: Mali Simulator', () => {
  let simulator: AdversarialSimulator;

  beforeEach(() => {
    simulator = new AdversarialSimulator();
  });

  test('evaluates 1000 decisions per second', () => {
    const decisions = Array(1000)
      .fill(0)
      .map((_, i) => ({ content: `Decision ${i}` }));

    const start = performance.now();
    decisions.forEach((d) => simulator.evaluate(d));
    const elapsed = performance.now() - start;

    const throughput = (1000 / elapsed) * 1000; // per second
    expect(throughput).toBeGreaterThan(1000); // > 1000 decisions/sec
  });
});
```

---

## Security Testing

### 1. Injection Prevention

#### Test: `__tests__/security/injection.test.ts`
```typescript
import { InjectionDetector } from '../../packages/tool-gateway/src/domain/InjectionDetector';

describe('Security: Injection Detection', () => {
  let detector: InjectionDetector;

  beforeEach(() => {
    detector = new InjectionDetector();
  });

  const injectionPayloads = [
    '{{ __import__("os").system("rm -rf /") }}',
    '{% for item in items %}',
    '<%= malicious %>',
    '<?php system($_GET["cmd"]); ?>',
    '`cat /etc/passwd`',
    '$(whoami)',
  ];

  injectionPayloads.forEach((payload) => {
    test(`blocks: ${payload.substring(0, 30)}...`, () => {
      expect(detector.scan(payload)).toBe(true);
    });
  });
});
```

### 2. Tenant Isolation

#### Test: `__tests__/security/tenant-isolation.test.ts`
```typescript
import { MemoryManager } from '../../packages/memory-core/src';

describe('Security: Tenant Isolation', () => {
  let memoryManager: MemoryManager;

  beforeEach(() => {
    memoryManager = new MemoryManager();
  });

  test('tenant1 cannot access tenant2 data', async () => {
    // Store secret in tenant1
    await memoryManager.writeMemory(
      {
        type: 'semantic',
        id: 'secret-key',
        data: { secret: 'TENANT_1_SECRET_KEY' },
        timestamp: new Date().toISOString(),
      },
      { source: 'domain', tenant_id: 't1', task_id: 'setup' }
    );

    // Try to access from tenant2
    const layer2 = memoryManager.createAccessLayer('t2');
    const retrieved = layer2.getSemantic('secret-key');

    expect(retrieved).toBeUndefined();
  });
});
```

---

## Observability & Debugging

### 1. Trace Collection

```typescript
import { withTraceContext, getTracer } from '@pamasmma/shared';

// Usage in application
withTraceContext('tenant-1', 'task-123', (span) => {
  span.addEvent('processing_started');
  // ... do work ...
  span.addEvent('processing_complete');
});
```

### 2. Metrics Exposure

```bash
# Prometheus metrics at /:9464/metrics
# Example metrics:
http_request_duration_seconds{service="orchestrator",route="/api/task"} 0.045
injection_attempts_total 3
mali_block_total 1
agent_drift_warnings_total 0
```

### 3. Structured Logging

```typescript
console.log('[OrchestratorAppService] Creating task', {
  tenant_id,
  type,
  timestamp: new Date().toISOString(),
});
```

---

## CI/CD Pipeline

### GitHub Actions Workflow: `.github/workflows/test.yml`

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: '18'
      - run: npm ci
      - run: npm test -- --coverage
      - run: npm run build
```

---

## Running Tests

### All Tests
```bash
npm test
```

### Specific Package
```bash
npm test -- --testPathPattern=orchestrator
```

### With Coverage
```bash
npm test -- --coverage
```

### Watch Mode
```bash
npm test -- --watch
```

### Performance Tests Only
```bash
npm test -- --testPathPattern=performance
```

---

## Test Checklist Before Release

- [ ] All unit tests passing
- [ ] All integration tests passing
- [ ] E2E workflows validated
- [ ] Injection payloads blocked
- [ ] Tenant isolation verified
- [ ] Latency < 10ms per operation
- [ ] Throughput > 1000 ops/sec
- [ ] Zero memory leaks
- [ ] Mali verdicts accurate (>95%)
- [ ] All event schemas validated
- [ ] Trace collection working
- [ ] Metrics exported correctly

---

## References

- [Jest Documentation](https://jestjs.io/)
- [Supertest](https://github.com/visionmedia/supertest)
- [OpenTelemetry](https://opentelemetry.io/)
- [Prometheus](https://prometheus.io/)
