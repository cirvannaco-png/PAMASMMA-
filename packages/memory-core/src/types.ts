export interface MemoryEntry {
  id: string;
  type: 'episodic' | 'semantic';
  data: Record<string, unknown>;
  timestamp: string;
  version?: number;
  tenant_id?: string;
}

export interface EpisodicRecord extends MemoryEntry {
  type: 'episodic';
  task_id: string;
  event_sequence: number;
}

export interface SemanticFact extends MemoryEntry {
  type: 'semantic';
  category: string;
  confidence: number;
}