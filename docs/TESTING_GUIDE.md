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

#### Test: Result Type
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
});
```

#### Test: Schema Validator
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
    const invalidEvent = { type: 'task.created' };
    expect(validateEvent(invalidEvent as any)).toBe(false);
  });
});
```

### 2. Memory-Core Tests
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
      data: { event: 'task_completed' },
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
    expect(retrieved?.tenant_id).toBe('t1');
  });
});
```

### 3. Mali Engine Tests
```typescript
import { AdversarialSimulator } from '../src/domain/AdversarialSimulator';

describe('Mali Adversarial Simulator', () => {
  let simulator: AdversarialSimulator;

  beforeEach(() => {
    simulator = new AdversarialSimulator();
  });

  test('rejects promotional spam', () => {
    const result = simulator.evaluate({
      content: 'Get 100% free premium guaranteed!',
    });
    expect(result.verdict).toBe('reject');
    expect(result.risk_score).toBeGreaterThan(0.7);
  });

  test('approves safe content', () => {
    const result = simulator.evaluate({
      content: 'Our verified product features',
    });
    expect(result.verdict).toBe('approve');
  });
});
```

---

## Integration Testing

### Orchestrator Integration
```typescript
import { OrchestratorAppService } from '../src/application/orchestratorAppService';
import { TaskCreator, TaskRouter } from '../src/domain/taskManagement';
import { MemoryManager } from '@pamasmma/memory-core';
import { IEventBus } from '@pamasmma/shared';

class MockEventBus implements IEventBus {
  events: any[] = [];
  async emit(event: any) { this.events.push(event); }
  subscribe() {}
}

describe('OrchestratorAppService Integration', () => {
  let service: OrchestratorAppService;
  let eventBus: MockEventBus;

  beforeEach(() => {
    eventBus = new MockEventBus();
    service = new OrchestratorAppService(
      new TaskCreator(),
      new TaskRouter(),
      new MemoryManager(),
      eventBus
    );
  });

  test('creates task, stores in memory, and emits event', async () => {
    const taskId = await service.createAndRouteTask('t1', 'content', { title: 'Test' });
    expect(taskId).toBeDefined();
    expect(eventBus.events.length).toBe(1);
    expect(eventBus.events[0].type).toBe('task.created');
  });
});
```

### Tool Gateway Integration
```typescript
import { ToolExecutionService } from '../src/application/ToolExecutionService';
import { ToolRegistry } from '../src/domain/ToolRegistry';
import { InjectionDetector } from '../src/domain/InjectionDetector';
import { IMaliService, IMCPClient, IEventBus } from '@pamasmma/shared';

class MockMaliService implements IMaliService {
  async evaluate(): Promise<'approve' | 'revise' | 'reject'> { return 'approve'; }
}

class MockMCPClient implements IMCPClient {
  async call() { return { status: 'success' }; }
}

class MockEventBus implements IEventBus {
  events: any[] = [];
  async emit(event: any) { this.events.push(event); }
  subscribe() {}
}

describe('ToolExecutionService', () => {
  let service: ToolExecutionService;

  beforeEach(() => {
    service = new ToolExecutionService(
      new ToolRegistry(),
      new InjectionDetector(),
      new MockMaliService(),
      new MockMCPClient(),
      new MockEventBus()
    );
  });

  test('rejects injection attacks', async () => {
    const result = await service.execute('test', '{{ injection }}', {
      tenant_id: 't1',
      task_id: 'task1',
      trace_id: 'trace1',
    });
    expect(result.ok).toBe(false);
    expect(result.error.code).toBe('INJECTION_BLOCKED');
  });
});
```

---

## End-to-End Testing

### Full Request Flow
```typescript
import request from 'supertest';
import express from 'express';
import { OrchestratorAppService } from '../src/application/orchestratorAppService';
import { orchestratorRoutes } from '../src/presentation/routes';

describe('Orchestrator E2E', () => {
  let app: express.Application;

  beforeEach(() => {
    const service = new OrchestratorAppService(
      new TaskCreator(),
      new TaskRouter(),
      new MemoryManager(),
      new MockEventBus()
    );
    app = express();
    app.use(express.json());
    app.use('/api', orchestratorRoutes(service));
  });

  test('POST /api/task returns task_id', async () => {
    const res = await request(app)
      .post('/api/task')
      .send({
        tenant_id: 't1',
        type: 'content',
        input: { title: 'Test' },
      });
    expect(res.status).toBe(200);
    expect(res.body.task_id).toBeDefined();
  });
});
```

---

## Performance Testing

### Latency Benchmarks
```typescript
describe('Performance: Task Creation', () => {
  test('creates task in < 10ms', async () => {
    const service = new OrchestratorAppService(...);
    const start = performance.now();
    for (let i = 0; i < 100; i++) {
      await service.createAndRouteTask('t1', 'content', { i });
    }
    const avgLatency = (performance.now() - start) / 100;
    expect(avgLatency).toBeLessThan(10);
  });
});
```

---

## Security Testing

### Injection Detection
```typescript
describe('Security: Injection Prevention', () => {
  const payloads = [
    '{{ malicious }}',
    '<?php system("ls"); ?>',
    '`whoami`',
  ];
  payloads.forEach((p) => {
    test(`blocks: ${p}`, () => {
      expect(detector.scan(p)).toBe(true);
    });
  });
});
```

### Tenant Isolation
```typescript
test('tenant1 cannot access tenant2 data', async () => {
  await memoryManager.writeMemory(
    { type: 'semantic', id: 'secret', data: { value: 'SECRET' }, timestamp: new Date().toISOString() },
    { source: 'domain', tenant_id: 't1', task_id: 'setup' }
  );
  const layer2 = memoryManager.createAccessLayer('t2');
  expect(layer2.getSemantic('secret')).toBeUndefined();
});
```

---

## Running Tests

```bash
# All tests
npm test

# Specific package
npm test -- --testPathPattern=orchestrator

# With coverage
npm test -- --coverage

# Watch mode
npm test -- --watch

# Performance only
npm test -- --testPathPattern=performance
```

---

## Pre-Release Checklist

- [ ] All unit tests passing
- [ ] All integration tests passing
- [ ] E2E workflows validated
- [ ] Injection payloads blocked
- [ ] Tenant isolation verified
- [ ] Latency < 10ms per operation
- [ ] Throughput > 1000 ops/sec
- [ ] Mali verdicts accurate (>95%)
- [ ] Event schemas validated
- [ ] Trace collection working
- [ ] Metrics exported correctly
