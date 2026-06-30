import { ShortTermMemory } from './stores/ShortTermMemory';
import { LongTermMemory } from './stores/LongTermMemory';
import { MemoryEntry, EpisodicRecord, SemanticFact } from './types';
import { generateUUID } from '@pamasmma/shared';

export class MemoryManager {
  private stm = new ShortTermMemory();
  private ltm = new LongTermMemory();

  async writeMemory(
    entry: MemoryEntry,
    context: { source: string; tenant_id: string; task_id: string }
  ): Promise<void> {
    if (context.source !== 'domain') {
      throw new Error('Unauthorized memory write source');
    }
    // Add version stamp
    const versionedEntry = {
      ...entry,
      version: Date.now(),
      tenant_id: context.tenant_id,
    };

    if (entry.type === 'episodic') {
      this.ltm.storeEpisodic(versionedEntry as EpisodicRecord);
    } else if (entry.type === 'semantic') {
      this.ltm.storeSemantic(versionedEntry as SemanticFact);
    }
    // Also update STM for immediate context
    this.stm.set(entry.id, versionedEntry);
  }

  createAccessLayer(tenantId: string): MemoryAccessLayer {
    return new MemoryAccessLayer(this.stm, this.ltm, tenantId);
  }
}

export class MemoryAccessLayer {
  constructor(
    private stm: ShortTermMemory,
    private ltm: LongTermMemory,
    private tenantId: string
  ) {}

  getEpisodic(taskId: string): EpisodicRecord | undefined {
    return this.ltm.getEpisodic(this.tenantId, taskId);
  }

  getSemantic(key: string): SemanticFact | undefined {
    return this.ltm.getSemantic(this.tenantId, key);
  }

  getFromSTM(id: string): MemoryEntry | undefined {
    return this.stm.get(id);
  }
}