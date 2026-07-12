import request from 'supertest';
import express from 'express';
import { OrchestratorAppService } from '../src/application/orchestratorAppService';
import { TaskCreator, TaskRouter, TaskStore } from '../src/domain/taskManagement';
import { MemoryManager } from '@pamasmma/memory-core';
import { IEventBus } from '@pamasmma/shared';
import { orchestratorRoutes } from '../src/presentation/routes';

class MockEventBus implements IEventBus {
  events: ReturnType<IEventBus['emit']> extends Promise<void>
    ? Parameters<IEventBus['emit']>[0][]
    : never[] = [] as Parameters<IEventBus['emit']>[0][];
  async emit(event: Parameters<IEventBus['emit']>[0]) {
    this.events.push(event);
  }
  subscribe() {}
}

function buildApp() {
  const bus = new MockEventBus();
  const taskStore = new TaskStore();
  const service = new OrchestratorAppService(
    new TaskCreator(),
    new TaskRouter(),
    taskStore,
    new MemoryManager(),
    bus
  );
  const app = express();
  app.use(express.json());
  app.use('/api', orchestratorRoutes(service));
  return { app, bus };
}

describe('GET /api/health', () => {
  it('returns 200 with status ok', async () => {
    const { app } = buildApp();
    const res = await request(app).get('/api/health');
    expect(res.status).toBe(200);
    expect(res.body.status).toBe('ok');
  });
});

describe('POST /api/task', () => {
  it('creates a task and returns 201 with task_id', async () => {
    const { app, bus } = buildApp();
    const res = await request(app)
      .post('/api/task')
      .send({ tenant_id: 't1', type: 'content', input: { title: 'Test' } });

    expect(res.status).toBe(201);
    expect(res.body.task_id).toBeDefined();
    expect(bus.events.length).toBe(1);
    expect(bus.events[0].type).toBe('task.created');
  });

  it('returns 400 when tenant_id is missing', async () => {
    const { app } = buildApp();
    const res = await request(app)
      .post('/api/task')
      .send({ type: 'content', input: {} });
    expect(res.status).toBe(400);
    expect(res.body.error).toMatch(/tenant_id/i);
  });

  it('returns 400 when type is invalid', async () => {
    const { app } = buildApp();
    const res = await request(app)
      .post('/api/task')
      .send({ tenant_id: 't1', type: 'unknown', input: {} });
    expect(res.status).toBe(400);
    expect(res.body.error).toMatch(/invalid type/i);
  });
});

describe('GET /api/tasks', () => {
  it('lists tasks for a tenant', async () => {
    const { app } = buildApp();
    await request(app)
      .post('/api/task')
      .send({ tenant_id: 't1', type: 'marketing', input: {} });

    const res = await request(app).get('/api/tasks?tenant_id=t1');
    expect(res.status).toBe(200);
    expect(res.body.count).toBe(1);
    expect(res.body.tasks[0].tenant_id).toBe('t1');
  });

  it('returns 400 without tenant_id', async () => {
    const { app } = buildApp();
    const res = await request(app).get('/api/tasks');
    expect(res.status).toBe(400);
  });

  it('returns empty list for unknown tenant', async () => {
    const { app } = buildApp();
    const res = await request(app).get('/api/tasks?tenant_id=nobody');
    expect(res.status).toBe(200);
    expect(res.body.count).toBe(0);
  });
});

describe('GET /api/task/:id', () => {
  it('returns a task by id', async () => {
    const { app } = buildApp();
    const create = await request(app)
      .post('/api/task')
      .send({ tenant_id: 't1', type: 'email', input: {} });
    const { task_id } = create.body;

    const res = await request(app).get(`/api/task/${task_id}?tenant_id=t1`);
    expect(res.status).toBe(200);
    expect(res.body.id).toBe(task_id);
  });

  it('returns 404 for non-existent task', async () => {
    const { app } = buildApp();
    const res = await request(app).get('/api/task/does-not-exist?tenant_id=t1');
    expect(res.status).toBe(404);
  });

  it('returns 404 when tenant does not match', async () => {
    const { app } = buildApp();
    const create = await request(app)
      .post('/api/task')
      .send({ tenant_id: 't1', type: 'content', input: {} });
    const { task_id } = create.body;

    const res = await request(app).get(`/api/task/${task_id}?tenant_id=other`);
    expect(res.status).toBe(404);
  });
});

describe('PATCH /api/task/:id/status', () => {
  it('updates task status', async () => {
    const { app } = buildApp();
    const create = await request(app)
      .post('/api/task')
      .send({ tenant_id: 't1', type: 'social', input: {} });
    const { task_id } = create.body;

    const res = await request(app)
      .patch(`/api/task/${task_id}/status`)
      .send({ tenant_id: 't1', status: 'completed' });

    expect(res.status).toBe(200);
    expect(res.body.status).toBe('completed');
  });

  it('returns 400 for invalid status', async () => {
    const { app } = buildApp();
    const res = await request(app)
      .patch('/api/task/some-id/status')
      .send({ tenant_id: 't1', status: 'invalid-status' });
    expect(res.status).toBe(400);
    expect(res.body.error).toMatch(/invalid status/i);
  });
});

describe('DELETE /api/task/:id', () => {
  it('cancels a task', async () => {
    const { app } = buildApp();
    const create = await request(app)
      .post('/api/task')
      .send({ tenant_id: 't1', type: 'content', input: {} });
    const { task_id } = create.body;

    const res = await request(app).delete(`/api/task/${task_id}?tenant_id=t1`);
    expect(res.status).toBe(200);
    expect(res.body.cancelled).toBe(true);
  });

  it('returns 404 for unknown task', async () => {
    const { app } = buildApp();
    const res = await request(app).delete('/api/task/ghost?tenant_id=t1');
    expect(res.status).toBe(404);
  });
});
