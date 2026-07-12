import { SelfHealingOrchestrator } from '../src/SelfHealingOrchestrator';
import { AgentVersionManager, PromptVersion } from '../src/AgentVersionManager';
import { IEventBus } from '@pamasmma/shared';

function makeEventBus(): jest.Mocked<IEventBus> {
  return { emit: jest.fn().mockResolvedValue(undefined) } as unknown as jest.Mocked<IEventBus>;
}

function makeVersionManager(): jest.Mocked<AgentVersionManager> {
  return {
    saveVersion: jest.fn(),
    getStableVersion: jest.fn().mockReturnValue(undefined),
    markAsStable: jest.fn(),
  } as unknown as jest.Mocked<AgentVersionManager>;
}

describe('SelfHealingOrchestrator', () => {
  let orchestrator: SelfHealingOrchestrator;
  let versionManager: jest.Mocked<AgentVersionManager>;
  let eventBus: jest.Mocked<IEventBus>;

  beforeEach(() => {
    versionManager = makeVersionManager();
    eventBus = makeEventBus();
    orchestrator = new SelfHealingOrchestrator(versionManager, eventBus);
  });

  describe('handleDrift', () => {
    it('always emits an agent.drift.detected event', async () => {
      await orchestrator.handleDrift('agent-x', 0.2);
      expect(eventBus.emit).toHaveBeenCalledTimes(1);
      expect(eventBus.emit).toHaveBeenCalledWith(
        expect.objectContaining({
          type: 'agent.drift.detected',
          agent_id: 'agent-x',
          drift_score: 0.2,
        })
      );
    });

    it('does NOT attempt rollback when drift ≤ 0.5', async () => {
      await orchestrator.handleDrift('agent-x', 0.5);
      expect(versionManager.getStableVersion).not.toHaveBeenCalled();
    });

    it('checks for a stable version when drift > 0.5', async () => {
      await orchestrator.handleDrift('agent-x', 0.6);
      expect(versionManager.getStableVersion).toHaveBeenCalledWith('agent-x');
    });

    it('logs a rollback when drift > 0.5 and a stable version exists', async () => {
      const stableVersion: PromptVersion = {
        version: 'v1000',
        promptHash: 'abc123',
        createdAt: new Date().toISOString(),
        isStable: true,
      };
      versionManager.getStableVersion.mockReturnValue(stableVersion);
      const logSpy = jest.spyOn(console, 'log').mockImplementation(() => {});

      await orchestrator.handleDrift('agent-y', 0.9);

      const logged = logSpy.mock.calls.map((c) => c[0] as string).join('');
      expect(logged).toMatch(/Rolling back/);
      logSpy.mockRestore();
    });

    it('handles the case where drift > 0.5 but no stable version exists', async () => {
      versionManager.getStableVersion.mockReturnValue(undefined);
      await expect(orchestrator.handleDrift('agent-z', 0.99)).resolves.not.toThrow();
    });

    it('emits the event with the correct schema_version and tenant_id', async () => {
      await orchestrator.handleDrift('agent-a', 0.1);
      expect(eventBus.emit).toHaveBeenCalledWith(
        expect.objectContaining({
          schema_version: 1,
          tenant_id: 'system',
        })
      );
    });
  });

  describe('healAgent', () => {
    it('returns healed: true and a new version string', async () => {
      versionManager.saveVersion.mockReturnValue({
        version: 'v9999',
        promptHash: 'v9999',
        createdAt: new Date().toISOString(),
        isStable: false,
      });

      const result = await orchestrator.healAgent('agent-z', { reason: 'test' });
      expect(result.healed).toBe(true);
      expect(typeof result.newVersion).toBe('string');
      expect(result.newVersion.length).toBeGreaterThan(0);
    });

    it('calls versionManager.saveVersion with the agent id', async () => {
      versionManager.saveVersion.mockReturnValue({
        version: 'v1',
        promptHash: 'h',
        createdAt: new Date().toISOString(),
        isStable: false,
      });
      await orchestrator.healAgent('agent-heal', {});
      expect(versionManager.saveVersion).toHaveBeenCalledWith('agent-heal', expect.any(String));
    });

    it('does not throw for empty diagnostics', async () => {
      versionManager.saveVersion.mockReturnValue({
        version: 'v1',
        promptHash: 'x',
        createdAt: '',
        isStable: false,
      });
      await expect(orchestrator.healAgent('agent-empty', {})).resolves.not.toThrow();
    });
  });
});
