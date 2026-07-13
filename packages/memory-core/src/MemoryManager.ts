import { ShortTermMemory } from './stores/ShortTermMemory';
import { LongTermMemory } from './stores/LongTermMemory';
import { ILongTermMemory } from './stores/ILongTermMemory';
import { MemoryEntry, EpisodicRecord, SemanticFact } from './types';
import { generateUUID } from '@pamasmma/shared';

export class MemoryManager {
  private stm: ShortTermMemory;
  private ltm: ILongTermMemory;

  /**
   * @param ltm - Long-term memory store to use.
   *   Defaults to the in-memory LongTermMemory (zero config, data lost on restart).
   *   Pass SqliteLongTermMemory (or any ILongTermMemory) for durable storage.
   */
  constructor(ltm?: ILongTermMemory) {
    this.stm = new ShortTermMemory();
    this.ltm = ltm ?? new LongTermMemory();
  }

  async writeMemory(
    entry: MemoryEntry,
    context: { source: string; tenant_id: string; task_id: string }
  ): Promise<void> {
    if (context.source !== 'domain') {
      throw new Error('Unauthorized memory write source');
    }
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
    private ltm: ILongTermMemory,
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
