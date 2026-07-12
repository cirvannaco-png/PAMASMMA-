import { ShortTermMemory } from '../src/stores/ShortTermMemory';
import { MemoryEntry } from '../src/types';

function makeEntry(id: string, data: Record<string, unknown> = {}): MemoryEntry {
  return {
    id,
    type: 'episodic',
    data,
    timestamp: new Date().toISOString(),
  };
}

describe('ShortTermMemory', () => {
  let stm: ShortTermMemory;

  beforeEach(() => {
    stm = new ShortTermMemory();
  });

  it('stores and retrieves an entry by id', () => {
    const entry = makeEntry('e1', { msg: 'hello' });
    stm.set('e1', entry);
    expect(stm.get('e1')).toEqual(entry);
  });

  it('returns undefined for a missing id', () => {
    expect(stm.get('not-here')).toBeUndefined();
  });

  it('overwrites an existing entry with the same id', () => {
    stm.set('e1', makeEntry('e1', { v: 1 }));
    stm.set('e1', makeEntry('e1', { v: 2 }));
    expect(stm.get('e1')?.data['v']).toBe(2);
  });

  it('clears all entries', () => {
    stm.set('a', makeEntry('a'));
    stm.set('b', makeEntry('b'));
    stm.clear();
    expect(stm.get('a')).toBeUndefined();
    expect(stm.get('b')).toBeUndefined();
  });

  it('evicts the oldest entry when maxSize (1000) is reached', () => {
    // Fill to capacity
    for (let i = 0; i < 1000; i++) {
      stm.set(`key-${i}`, makeEntry(`key-${i}`));
    }
    // First entry should still be present
    expect(stm.get('key-0')).toBeDefined();

    // Adding one more triggers eviction of key-0
    stm.set('key-1000', makeEntry('key-1000'));
    expect(stm.get('key-0')).toBeUndefined();
    expect(stm.get('key-1000')).toBeDefined();
  });

  it('preserves the most recently set entry under eviction pressure', () => {
    for (let i = 0; i < 1001; i++) {
      stm.set(`k-${i}`, makeEntry(`k-${i}`));
    }
    // Only k-0 should have been evicted; k-1 through k-1000 should remain
    expect(stm.get('k-1000')).toBeDefined();
    expect(stm.get('k-500')).toBeDefined();
  });
});
