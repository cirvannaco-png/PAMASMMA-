import { MemoryEntry, EpisodicRecord, SemanticFact } from './types';

export class ShortTermMemory {
  private cache = new Map<string, MemoryEntry>();
  private maxSize = 1000;

  set(id: string, entry: MemoryEntry): void {
    if (this.cache.size >= this.maxSize) {
      const firstKey = this.cache.keys().next().value;
      this.cache.delete(firstKey);
    }
    this.cache.set(id, entry);
  }

  get(id: string): MemoryEntry | undefined {
    return this.cache.get(id);
  }

  clear(): void {
    this.cache.clear();
  }
}