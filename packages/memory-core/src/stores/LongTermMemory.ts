import { EpisodicRecord, SemanticFact } from '../types';
import { ILongTermMemory } from './ILongTermMemory';

/**
 * In-process long-term memory store backed by plain Maps.
 * Zero config — useful for tests and local development where persistence is not needed.
 * Data is lost when the process exits; use SqliteLongTermMemory for durable storage.
 */
export class LongTermMemory implements ILongTermMemory {
  private episodic = new Map<string, EpisodicRecord>();
  private semantic = new Map<string, SemanticFact>();

  storeEpisodic(record: EpisodicRecord): void {
    const key = `${record.tenant_id ?? ''}:${record.id}`;
    this.episodic.set(key, record);
  }

  getEpisodic(tenantId: string, taskId: string): EpisodicRecord | undefined {
    const key = `${tenantId}:${taskId}`;
    return this.episodic.get(key);
  }

  storeSemantic(fact: SemanticFact): void {
    const key = `${fact.tenant_id ?? ''}:${fact.id}`;
    this.semantic.set(key, fact);
  }

  getSemantic(tenantId: string, factId: string): SemanticFact | undefined {
    const key = `${tenantId}:${factId}`;
    return this.semantic.get(key);
  }
}
