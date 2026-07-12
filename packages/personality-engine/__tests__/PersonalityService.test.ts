import { PersonalityService } from '../src/application/PersonalityService';
import { IdentityCoherenceEngine, DriftReport } from '../src/domain/IdentityCoherenceEngine';
import { SelfHealingOrchestrator } from '@pamasmma/self-healing';
import { MemoryManager } from '@pamasmma/memory-core';
import { IEventBus } from '@pamasmma/shared';

function makeDriftReport(overrides: Partial<DriftReport> = {}): DriftReport {
  return {
    driftScore: 0.1,
    warning: false,
    shiftingDimensions: [],
    ...overrides,
  };
}

function makeAccessLayer(baseline?: number[]) {
  return {
    getEpisodic: jest.fn().mockReturnValue(
      baseline ? { id: 'personality-baseline', type: 'episodic', data: { vector: baseline }, timestamp: '' } : undefined
    ),
    getSemantic: jest.fn().mockReturnValue(undefined),
    getFromSTM: jest.fn().mockReturnValue(undefined),
  };
}

function makeMemoryManager(baseline?: number[]): jest.Mocked<MemoryManager> {
  return {
    writeMemory: jest.fn().mockResolvedValue(undefined),
    createAccessLayer: jest.fn().mockReturnValue(makeAccessLayer(baseline)),
  } as unknown as jest.Mocked<MemoryManager>;
}

function makeCoherenceEngine(report: DriftReport): jest.Mocked<IdentityCoherenceEngine> {
  return {
    checkDrift: jest.fn().mockReturnValue(report),
  } as unknown as jest.Mocked<IdentityCoherenceEngine>;
}

function makeSelfHealing(): jest.Mocked<SelfHealingOrchestrator> {
  return {
    handleDrift: jest.fn().mockResolvedValue(undefined),
    healAgent: jest.fn().mockResolvedValue({ healed: true, newVersion: 'v1' }),
  } as unknown as jest.Mocked<SelfHealingOrchestrator>;
}

function makeEventBus(): jest.Mocked<IEventBus> {
  return { emit: jest.fn().mockResolvedValue(undefined) } as unknown as jest.Mocked<IEventBus>;
}

describe('PersonalityService', () => {
  const baseline = [0.5, 0.6, 0.7, 0.8];
  const current = [0.5, 0.6, 0.7, 0.8];

  let service: PersonalityService;
  let memoryManager: jest.Mocked<MemoryManager>;
  let coherenceEngine: jest.Mocked<IdentityCoherenceEngine>;
  let selfHealing: jest.Mocked<SelfHealingOrchestrator>;
  let eventBus: jest.Mocked<IEventBus>;

  beforeEach(() => {
    memoryManager = makeMemoryManager(baseline);
    coherenceEngine = makeCoherenceEngine(makeDriftReport());
    selfHealing = makeSelfHealing();
    eventBus = makeEventBus();
    service = new PersonalityService(memoryManager, coherenceEngine, selfHealing, eventBus);
  });

  describe('assessCurrentBehavior', () => {
    it('throws when no baseline personality is found in memory', async () => {
      memoryManager = makeMemoryManager(undefined); // no baseline
      service = new PersonalityService(memoryManager, coherenceEngine, selfHealing, eventBus);

      await expect(
        service.assessCurrentBehavior('tenant-1', 'agent-1', current)
      ).rejects.toThrow('No baseline personality found');
    });

    it('delegates drift calculation to the coherence engine', async () => {
      await service.assessCurrentBehavior('tenant-1', 'agent-1', current);
      expect(coherenceEngine.checkDrift).toHaveBeenCalledWith(baseline, current);
    });

    it('returns the drift report from the coherence engine', async () => {
      const report = makeDriftReport({ driftScore: 0.15, warning: false });
      coherenceEngine.checkDrift.mockReturnValue(report);

      const result = await service.assessCurrentBehavior('tenant-1', 'agent-1', current);
      expect(result).toEqual(report);
    });

    it('calls selfHealing.handleDrift when warning is true', async () => {
      coherenceEngine.checkDrift.mockReturnValue(makeDriftReport({ driftScore: 0.8, warning: true }));

      await service.assessCurrentBehavior('tenant-1', 'agent-x', current);
      expect(selfHealing.handleDrift).toHaveBeenCalledWith('agent-x', 0.8);
    });

    it('does NOT call selfHealing.handleDrift when warning is false', async () => {
      coherenceEngine.checkDrift.mockReturnValue(makeDriftReport({ driftScore: 0.1, warning: false }));

      await service.assessCurrentBehavior('tenant-1', 'agent-x', current);
      expect(selfHealing.handleDrift).not.toHaveBeenCalled();
    });

    it('creates an access layer scoped to the correct tenant', async () => {
      await service.assessCurrentBehavior('tenant-abc', 'agent-1', current);
      expect(memoryManager.createAccessLayer).toHaveBeenCalledWith('tenant-abc');
    });

    it('uses the baseline from the personality-baseline episodic record', async () => {
      const customBaseline = [0.1, 0.2, 0.3];
      memoryManager = makeMemoryManager(customBaseline);
      service = new PersonalityService(memoryManager, coherenceEngine, selfHealing, eventBus);

      await service.assessCurrentBehavior('tenant-1', 'agent-1', [0.2, 0.2, 0.2]);
      expect(coherenceEngine.checkDrift).toHaveBeenCalledWith(customBaseline, [0.2, 0.2, 0.2]);
    });
  });
});
