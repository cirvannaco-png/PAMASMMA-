import { MemoryManager, MemoryAccessLayer } from '../src/MemoryManager';
import { MemoryEntry } from '../src/types';

function makeEntry(overrides: Partial<MemoryEntry> = {}): MemoryEntry {
  return {
    id: 'entry-1',
    type: 'episodic',
    data: { key: 'value' },
    timestamp: new Date().toISOString(),
    ...overrides,
  };
}

describe('MemoryManager', () => {
  let manager: MemoryManager;

  beforeEach(() => {
    manager = new MemoryManager();
  });

  describe('writeMemory', () => {
    it('rejects writes from non-domain sources', async () => {
      const entry = makeEntry({ type: 'episodic' });
      await expect(
        manager.writeMemory(entry, { source: 'external', tenant_id: 't1', task_id: 'task-1' })
      ).rejects.toThrow('Unauthorized memory write source');
    });

    it('stores an episodic entry and makes it retrievable', async () => {
      const entry = makeEntry({ id: 'ep-1', type: 'episodic' });
      await manager.writeMemory(entry, { source: 'domain', tenant_id: 't1', task_id: 'task-1' });

      const layer = manager.createAccessLayer('t1');
      const result = layer.getFromSTM('ep-1');
      expect(result).toBeDefined();
      expect(result?.id).toBe('ep-1');
    });

    it('stamps a version number on every write', async () => {
      const entry = makeEntry({ id: 'ep-2', type: 'episodic' });
      await manager.writeMemory(entry, { source: 'domain', tenant_id: 't1', task_id: 'task-2' });

      const layer = manager.createAccessLayer('t1');
      const result = layer.getFromSTM('ep-2');
      expect(typeof result?.version).toBe('number');
    });

    it('stores a semantic entry and makes it retrievable via LTM', async () => {
      const entry: MemoryEntry = {
        id: 'sem-1',
        type: 'semantic',
        data: { fact: 'TypeScript is typed JS' },
        timestamp: new Date().toISOString(),
      };
      await manager.writeMemory(entry, { source: 'domain', tenant_id: 't2', task_id: 'ignored' });

      const layer = manager.createAccessLayer('t2');
      const result = layer.getSemantic('sem-1');
      expect(result).toBeDefined();
      expect(result?.id).toBe('sem-1');
    });

    it('scopes episodic entries by tenant', async () => {
      const entry = makeEntry({ id: 'ep-scoped', type: 'episodic' });
      await manager.writeMemory(entry, { source: 'domain', tenant_id: 'tenant-A', task_id: 'task-x' });

      const wrongLayer = manager.createAccessLayer('tenant-B');
      expect(wrongLayer.getEpisodic('ep-scoped')).toBeUndefined();
    });
  });

  describe('createAccessLayer', () => {
    it('returns a MemoryAccessLayer bound to the given tenant', () => {
      const layer = manager.createAccessLayer('t-test');
      expect(layer).toBeInstanceOf(MemoryAccessLayer);
    });

    it('returns undefined for missing STM entries', () => {
      const layer = manager.createAccessLayer('t-empty');
      expect(layer.getFromSTM('does-not-exist')).toBeUndefined();
    });

    it('returns undefined for missing LTM episodic entries', () => {
      const layer = manager.createAccessLayer('t-empty');
      expect(layer.getEpisodic('does-not-exist')).toBeUndefined();
    });

    it('returns undefined for missing semantic facts', () => {
      const layer = manager.createAccessLayer('t-empty');
      expect(layer.getSemantic('does-not-exist')).toBeUndefined();
    });
  });
});
