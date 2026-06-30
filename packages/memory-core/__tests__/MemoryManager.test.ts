import { MemoryManager } from '../src/MemoryManager';
import { MemoryEntry } from '../src/types';

describe('MemoryManager', () => {
  let manager: MemoryManager;

  beforeEach(() => {
    manager = new MemoryManager();
  });

  test('writes episodic memory with version stamp', async () => {
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
    expect(retrieved?.version).toBeDefined();
  });

  test('throws on unauthorized write source', async () => {
    const entry: MemoryEntry = {
      id: 'ep-1',
      type: 'episodic',
      data: {},
      timestamp: new Date().toISOString(),
    };

    await expect(
      manager.writeMemory(entry, {
        source: 'unauthorized',
        tenant_id: 't1',
        task_id: 'task-1',
      })
    ).rejects.toThrow('Unauthorized memory write source');
  });
});
