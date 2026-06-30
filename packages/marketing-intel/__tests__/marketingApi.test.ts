import { MarketingIntelService } from '../src/application/MarketingIntelService';
import { MemoryManager } from '@pamasmma/memory-core';
import { IEventBus } from '@pamasmma/shared';

class MockEventBus implements IEventBus {
  events: any[] = [];
  async emit(event: any) {
    this.events.push(event);
  }
  subscribe() {}
}

describe('MarketingIntelService', () => {
  let service: MarketingIntelService;
  let eventBus: MockEventBus;

  beforeEach(() => {
    eventBus = new MockEventBus();
    service = new MarketingIntelService(new MemoryManager(), eventBus);
  });

  test('analyzes marketing decision', async () => {
    const result = await service.analyzeMarketingDecision(
      't1',
      'task1',
      {
        platform: 'instagram',
        engagement_rate: 0.85,
        content_type: 'video',
      }
    );

    expect(result.decision_id).toBe('task1');
    expect(result.ready_for_execution).toBe(true);
  });
});
