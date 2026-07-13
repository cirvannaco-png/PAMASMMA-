import { SqliteTaskStore } from '../src/infra/SqliteTaskStore';
import { Task } from '../src/domain/taskManagement';

function makeTask(overrides: Partial<Task> = {}): Task {
  const now = new Date().toISOString();
  return {
    id: `task-${Math.random().toString(36).slice(2)}`,
    tenant_id: 'tenant-1',
    type: 'content',
    input: { prompt: 'hello' },
    status: 'pending',
    created_at: now,
    updated_at: now,
    ...overrides,
  };
}

describe('SqliteTaskStore', () => {
  let store: SqliteTaskStore;

  beforeEach(() => {
    // ':memory:' gives a fresh in-process DB per test — no files, no cleanup
    store = new SqliteTaskStore(':memory:');
  });

  afterEach(() => {
    store.close();
  });

  describe('save / findById', () => {
    it('stores a task and retrieves it by id', () => {
      const task = makeTask({ id: 'abc-123' });
      store.save(task);
      const found = store.findById('abc-123');
      expect(found).toEqual(task);
    });

    it('returns undefined for an unknown id', () => {
      expect(store.findById('does-not-exist')).toBeUndefined();
    });

    it('overwrites an existing task on save (upsert)', () => {
      const task = makeTask({ id: 'dup' });
      store.save(task);
      store.save({ ...task, status: 'completed' });
      expect(store.findById('dup')?.status).toBe('completed');
    });

    it('round-trips a complex input object correctly', () => {
      const task = makeTask({ input: { nested: { a: 1 }, arr: [true, 'x'] } });
      store.save(task);
      expect(store.findById(task.id)?.input).toEqual(task.input);
    });
  });

  describe('findByTenant', () => {
    it('returns all tasks belonging to a tenant', () => {
      store.save(makeTask({ id: 't1-a', tenant_id: 'alpha' }));
      store.save(makeTask({ id: 't1-b', tenant_id: 'alpha' }));
      store.save(makeTask({ id: 't2-a', tenant_id: 'beta' }));

      const alphaJobs = store.findByTenant('alpha');
      expect(alphaJobs).toHaveLength(2);
      expect(alphaJobs.every((t) => t.tenant_id === 'alpha')).toBe(true);
    });

    it('returns an empty array when tenant has no tasks', () => {
      expect(store.findByTenant('nobody')).toEqual([]);
    });

    it('does not leak tasks across tenants', () => {
      store.save(makeTask({ id: 'x', tenant_id: 'alpha' }));
      expect(store.findByTenant('beta')).toHaveLength(0);
    });
  });

  describe('updateStatus', () => {
    it('updates status and returns the updated task', () => {
      const task = makeTask({ id: 'upd' });
      store.save(task);

      const updated = store.updateStatus('upd', 'completed');
      expect(updated?.status).toBe('completed');
    });

    it('updates updated_at timestamp', () => {
      const task = makeTask({ id: 'ts', updated_at: '2000-01-01T00:00:00.000Z' });
      store.save(task);
      store.updateStatus('ts', 'processing');
      const found = store.findById('ts');
      expect(found?.updated_at).not.toBe('2000-01-01T00:00:00.000Z');
    });

    it('returns undefined for an unknown id', () => {
      expect(store.updateStatus('ghost', 'completed')).toBeUndefined();
    });
  });

  describe('delete', () => {
    it('removes a task and returns true', () => {
      const task = makeTask({ id: 'del' });
      store.save(task);
      expect(store.delete('del')).toBe(true);
      expect(store.findById('del')).toBeUndefined();
    });

    it('returns false when deleting a non-existent task', () => {
      expect(store.delete('ghost')).toBe(false);
    });
  });
});
