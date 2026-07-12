import { LongTermMemory } from '../src/stores/LongTermMemory';
import { EpisodicRecord, SemanticFact } from '../src/types';

function makeEpisodic(overrides: Partial<EpisodicRecord> = {}): EpisodicRecord {
  return {
    id: 'ep-1',
    type: 'episodic',
    data: { action: 'test' },
    timestamp: new Date().toISOString(),
    tenant_id: 'tenant-1',
    task_id: 'task-1',
    event_sequence: 1,
    ...overrides,
  };
}

function makeSemantic(overrides: Partial<SemanticFact> = {}): SemanticFact {
  return {
    id: 'sem-1',
    type: 'semantic',
    data: { value: 42 },
    timestamp: new Date().toISOString(),
    tenant_id: 'tenant-1',
    category: 'test',
    confidence: 0.9,
    ...overrides,
  };
}

describe('LongTermMemory', () => {
  let ltm: LongTermMemory;

  beforeEach(() => {
    ltm = new LongTermMemory();
  });

  describe('episodic storage', () => {
    it('stores and retrieves an episodic record', () => {
      const record = makeEpisodic();
      ltm.storeEpisodic(record);
      expect(ltm.getEpisodic('tenant-1', 'ep-1')).toEqual(record);
    });

    it('keys by tenant_id so different tenants do not share records', () => {
      const a = makeEpisodic({ id: 'ep-shared', tenant_id: 'tenant-A' });
      const b = makeEpisodic({ id: 'ep-shared', tenant_id: 'tenant-B', data: { action: 'other' } });
      ltm.storeEpisodic(a);
      ltm.storeEpisodic(b);

      expect(ltm.getEpisodic('tenant-A', 'ep-shared')?.data.action).toBe('test');
      expect(ltm.getEpisodic('tenant-B', 'ep-shared')?.data.action).toBe('other');
    });

    it('overwrites an existing record with the same id', () => {
      ltm.storeEpisodic(makeEpisodic({ data: { action: 'first' } }));
      ltm.storeEpisodic(makeEpisodic({ data: { action: 'second' } }));
      expect(ltm.getEpisodic('tenant-1', 'ep-1')?.data.action).toBe('second');
    });

    it('returns undefined for a missing key', () => {
      expect(ltm.getEpisodic('tenant-x', 'nope')).toBeUndefined();
    });
  });

  describe('semantic storage', () => {
    it('stores and retrieves a semantic fact', () => {
      const fact = makeSemantic();
      ltm.storeSemantic(fact);
      expect(ltm.getSemantic('tenant-1', 'sem-1')).toEqual(fact);
    });

    it('isolates semantic facts by tenant', () => {
      ltm.storeSemantic(makeSemantic({ id: 'fact', tenant_id: 'tenant-A', confidence: 0.8 }));
      ltm.storeSemantic(makeSemantic({ id: 'fact', tenant_id: 'tenant-B', confidence: 0.5 }));

      expect(ltm.getSemantic('tenant-A', 'fact')?.confidence).toBe(0.8);
      expect(ltm.getSemantic('tenant-B', 'fact')?.confidence).toBe(0.5);
    });

    it('overwrites a fact with the same id', () => {
      ltm.storeSemantic(makeSemantic({ confidence: 0.6 }));
      ltm.storeSemantic(makeSemantic({ confidence: 0.95 }));
      expect(ltm.getSemantic('tenant-1', 'sem-1')?.confidence).toBe(0.95);
    });

    it('returns undefined for a missing semantic key', () => {
      expect(ltm.getSemantic('tenant-x', 'nope')).toBeUndefined();
    });
  });
});
