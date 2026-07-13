import { SqliteLongTermMemory } from '../src/stores/SqliteLongTermMemory';
import { EpisodicRecord, SemanticFact } from '../src/types';

function makeEpisodic(overrides: Partial<EpisodicRecord> = {}): EpisodicRecord {
  return {
    id: 'ep-1',
    type: 'episodic',
    tenant_id: 'tenant-1',
    task_id: 'task-abc',
    event_sequence: 1,
    data: { action: 'created' },
    timestamp: new Date().toISOString(),
    ...overrides,
  };
}

function makeSemantic(overrides: Partial<SemanticFact> = {}): SemanticFact {
  return {
    id: 'sem-1',
    type: 'semantic',
    tenant_id: 'tenant-1',
    category: 'brand',
    confidence: 0.9,
    data: { tone: 'friendly' },
    timestamp: new Date().toISOString(),
    ...overrides,
  };
}

describe('SqliteLongTermMemory', () => {
  let store: SqliteLongTermMemory;

  beforeEach(() => {
    store = new SqliteLongTermMemory(':memory:');
  });

  afterEach(() => {
    store.close();
  });

  // ── Episodic ──────────────────────────────────────────────────────────────

  describe('episodic records', () => {
    it('stores and retrieves an episodic record', () => {
      const record = makeEpisodic();
      store.storeEpisodic(record);
      const found = store.getEpisodic('tenant-1', 'ep-1');
      expect(found).toEqual(record);
    });

    it('returns undefined for a missing episodic key', () => {
      expect(store.getEpisodic('tenant-1', 'ghost')).toBeUndefined();
    });

    it('does not return a record scoped to a different tenant', () => {
      store.storeEpisodic(makeEpisodic({ tenant_id: 'alpha', id: 'ep-x' }));
      expect(store.getEpisodic('beta', 'ep-x')).toBeUndefined();
    });

    it('overwrites an existing record on re-store (upsert)', () => {
      store.storeEpisodic(makeEpisodic({ data: { v: 1 } }));
      store.storeEpisodic(makeEpisodic({ data: { v: 2 } }));
      expect(store.getEpisodic('tenant-1', 'ep-1')?.data).toEqual({ v: 2 });
    });

    it('round-trips nested data structures correctly', () => {
      const record = makeEpisodic({ data: { nested: { arr: [1, 2, 3] } } });
      store.storeEpisodic(record);
      expect(store.getEpisodic('tenant-1', 'ep-1')?.data).toEqual(record.data);
    });
  });

  // ── Semantic ──────────────────────────────────────────────────────────────

  describe('semantic facts', () => {
    it('stores and retrieves a semantic fact', () => {
      const fact = makeSemantic();
      store.storeSemantic(fact);
      const found = store.getSemantic('tenant-1', 'sem-1');
      expect(found).toEqual(fact);
    });

    it('returns undefined for a missing semantic key', () => {
      expect(store.getSemantic('tenant-1', 'ghost')).toBeUndefined();
    });

    it('does not return a fact scoped to a different tenant', () => {
      store.storeSemantic(makeSemantic({ tenant_id: 'alpha', id: 'sem-x' }));
      expect(store.getSemantic('beta', 'sem-x')).toBeUndefined();
    });

    it('overwrites an existing fact on re-store (upsert)', () => {
      store.storeSemantic(makeSemantic({ confidence: 0.7 }));
      store.storeSemantic(makeSemantic({ confidence: 0.95 }));
      expect(store.getSemantic('tenant-1', 'sem-1')?.confidence).toBe(0.95);
    });
  });

  // ── Isolation between stores ───────────────────────────────────────────────

  describe('two independent :memory: stores', () => {
    it('do not share state', () => {
      const store2 = new SqliteLongTermMemory(':memory:');
      store.storeEpisodic(makeEpisodic({ id: 'shared-id' }));
      expect(store2.getEpisodic('tenant-1', 'shared-id')).toBeUndefined();
      store2.close();
    });
  });
});
