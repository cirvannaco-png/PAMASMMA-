import { EpisodicRecord, SemanticFact } from '../types';

/**
 * Persistence contract for long-term memory.
 * Two implementations exist:
 *  - LongTermMemory: in-process Map, zero config, data lost on restart (tests / local dev).
 *  - SqliteLongTermMemory: SQLite-backed, survives restarts, zero infra (dev / staging).
 * A Postgres adapter can implement this interface for production without changing any caller.
 */
export interface ILongTermMemory {
  storeEpisodic(record: EpisodicRecord): void;
  getEpisodic(tenantId: string, taskId: string): EpisodicRecord | undefined;
  storeSemantic(fact: SemanticFact): void;
  getSemantic(tenantId: string, factId: string): SemanticFact | undefined;
}
