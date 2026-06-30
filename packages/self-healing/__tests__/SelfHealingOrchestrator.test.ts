import { SelfHealingOrchestrator } from '../src/SelfHealingOrchestrator';
import { AgentVersionManager } from '../src/AgentVersionManager';
import { IEventBus } from '@pamasmma/shared';

class MockEventBus implements IEventBus {
  events: any[] = [];
  async emit(event: any) {
    this.events.push(event);
  }
  subscribe() {}
}

describe('SelfHealingOrchestrator', () => {
  let orchestrator: SelfHealingOrchestrator;
  let versionManager: AgentVersionManager;
  let eventBus: MockEventBus;

  beforeEach(() => {
    versionManager = new AgentVersionManager();
    eventBus = new MockEventBus();
    orchestrator = new SelfHealingOrchestrator(versionManager, eventBus);
  });

  test('emits drift detected event', async () => {
    await orchestrator.handleDrift('agent-1', 0.75);
    expect(eventBus.events.length).toBe(1);
    expect(eventBus.events[0].type).toBe('agent.drift.detected');
    expect(eventBus.events[0].drift_score).toBe(0.75);
  });

  test('heals agent', async () => {
    const result = await orchestrator.healAgent('agent-1', { issue: 'off-topic' });
    expect(result.healed).toBe(true);
    expect(result.newVersion).toBeDefined();
  });
});
