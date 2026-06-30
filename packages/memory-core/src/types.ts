export interface MemoryEntry {id: string; type: 'episodic' | 'semantic'; data: Record<string, unknown>; timestamp: string; version?: number; tenant_id?: string;}
export interface EpisodicRecord extends MemoryEntry {type: 'episodic';}
export interface SemanticFact extends MemoryEntry {type: 'semantic';}