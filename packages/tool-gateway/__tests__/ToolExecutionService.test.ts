import { ToolExecutionService } from '../src/application/ToolExecutionService';
import { ToolRegistry } from '../src/domain/ToolRegistry';
import { InjectionDetector } from '../src/domain/InjectionDetector';
import { IMaliService, IMCPClient, IEventBus } from '@pamasmma/shared';

class MockMaliService implements IMaliService {
  async evaluate(): Promise<'approve' | 'revise' | 'reject'> {
    return 'approve';
  }
}

class MockMCPClient implements IMCPClient {
  async call(): Promise<unknown> {
    return { status: 'success', data: 'mock result' };
  }
}

class MockEventBus implements IEventBus {
  events: any[] = [];
  async emit(event: any) {
    this.events.push(event);
  }
  subscribe() {}
}

describe('ToolExecutionService', () => {
  let service: ToolExecutionService;
  let registry: ToolRegistry;
  let eventBus: MockEventBus;

  beforeEach(() => {
    registry = new ToolRegistry();
    eventBus = new MockEventBus();
    service = new ToolExecutionService(
      registry,
      new InjectionDetector(),
      new MockMaliService(),
      new MockMCPClient(),
      eventBus
    );
  });

  test('returns error for non-existent tool', async () => {
    const result = await service.execute('nonexistent', {}, {
      tenant_id: 't1',
      task_id: 'task1',
      trace_id: 'trace1',
    });
    expect(result.ok).toBe(false);
    expect(result.error.code).toBe('TOOL_NOT_FOUND');
  });

  test('detects injection and rejects', async () => {
    const result = await service.execute('test_tool', '{{malicious}}', {
      tenant_id: 't1',
      task_id: 'task1',
      trace_id: 'trace1',
    });
    expect(result.ok).toBe(false);
    expect(result.error.code).toBe('INJECTION_BLOCKED');
  });
});
