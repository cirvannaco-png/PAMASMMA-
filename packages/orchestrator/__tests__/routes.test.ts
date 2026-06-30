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

describe('Orchestrator Routes', () => {
  let bus: MockEventBus;
  let service: OrchestratorAppService;
  let app: express.Application;

  beforeEach(() => {
    bus = new MockEventBus();
    service = new OrchestratorAppService(new TaskCreator(), new TaskRouter(), new MemoryManager(), bus);
    app = express();
    app.use(express.json());
    app.use('/api', orchestratorRoutes(service));
  });

  test('POST /api/task creates task and returns id', async () => {
    const res = await request(app)
      .post('/api/task')
      .send({ tenant_id: 't1', type: 'content', input: { title: 'Test' } });

    expect(res.status).toBe(200);
    expect(res.body.task_id).toBeDefined();
    expect(bus.events.length).toBe(1);
    expect(bus.events[0].type).toBe('task.created');
  });
});
