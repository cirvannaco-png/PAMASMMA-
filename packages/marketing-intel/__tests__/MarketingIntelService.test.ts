import { MarketingIntelService } from '../src/application/MarketingIntelService';
import { MemoryManager } from '@pamasmma/memory-core';
import { IEventBus } from '@pamasmma/shared';

function makeMemoryManager(): jest.Mocked<MemoryManager> {
  return {
    writeMemory: jest.fn().mockResolvedValue(undefined),
    createAccessLayer: jest.fn().mockReturnValue({
      getEpisodic: jest.fn().mockReturnValue(undefined),
      getSemantic: jest.fn().mockReturnValue(undefined),
      getFromSTM: jest.fn().mockReturnValue(undefined),
    }),
  } as unknown as jest.Mocked<MemoryManager>;
}

function makeEventBus(): jest.Mocked<IEventBus> {
  return { emit: jest.fn().mockResolvedValue(undefined) } as unknown as jest.Mocked<IEventBus>;
}

describe('MarketingIntelService', () => {
  let service: MarketingIntelService;
  let memoryManager: jest.Mocked<MemoryManager>;
  let eventBus: jest.Mocked<IEventBus>;

  beforeEach(() => {
    memoryManager = makeMemoryManager();
    eventBus = makeEventBus();
    service = new MarketingIntelService(memoryManager, eventBus);
  });

  describe('analyzeMarketingDecision', () => {
    it('returns a result object with the expected shape', async () => {
      const result = await service.analyzeMarketingDecision('tenant-1', 'task-1', {
        platform: 'instagram',
        engagement_rate: 0.05,
      });

      expect(result).toMatchObject({
        decision_id: 'task-1',
        ready_for_execution: true,
      });
    });

    it('sets guidelines_applied to false when no guidelines are in memory', async () => {
      const result = await service.analyzeMarketingDecision('tenant-1', 'task-2', {
        platform: 'twitter',
      });
      expect(result.guidelines_applied).toBe(false);
    });

    it('includes a mali critique in the result', async () => {
      const result = await service.analyzeMarketingDecision('tenant-1', 'task-3', {
        platform: 'facebook',
        engagement_rate: 0.1,
      });
      expect(result).toHaveProperty('critique');
    });

    it('records an observational signal (does not throw with unknown platform)', async () => {
      await expect(
        service.analyzeMarketingDecision('tenant-1', 'task-4', {})
      ).resolves.not.toThrow();
    });

    it('propagates errors from underlying services', async () => {
      // Make the memory manager throw on createAccessLayer
      memoryManager.createAccessLayer.mockImplementationOnce(() => {
        throw new Error('Memory unavailable');
      });

      await expect(
        service.analyzeMarketingDecision('tenant-x', 'task-err', { platform: 'x' })
      ).rejects.toThrow('Memory unavailable');
    });
  });
});
