import Database from 'better-sqlite3';
import { Task, TaskStatus, ITaskStore } from '../domain/taskManagement';

/**
 * SQLite-backed task store.
 *
 * Implements ITaskStore with the same contract as the in-memory TaskStore but
 * persists to disk — restarts don't wipe the task queue.
 *
 * Pass ':memory:' as dbPath in tests so each suite gets a fresh in-process DB
 * with zero cleanup overhead:
 *   const store = new SqliteTaskStore(':memory:');
 */
export class SqliteTaskStore implements ITaskStore {
  private readonly db: Database.Database;

  constructor(dbPath: string = process.env['DATABASE_PATH'] ?? './pamasmma.db') {
    this.db = new Database(dbPath);
    this.migrate();
  }

  // ── Schema ───────────────────────────────────────────────────────────────

  private migrate(): void {
    this.db.exec(`
      CREATE TABLE IF NOT EXISTS tasks (
        id          TEXT PRIMARY KEY,
        tenant_id   TEXT NOT NULL,
        type        TEXT NOT NULL,
        input       TEXT NOT NULL DEFAULT '{}',
        status      TEXT NOT NULL DEFAULT 'pending',
        created_at  TEXT NOT NULL,
        updated_at  TEXT NOT NULL
      );

      CREATE INDEX IF NOT EXISTS idx_tasks_tenant_id ON tasks(tenant_id);
      CREATE INDEX IF NOT EXISTS idx_tasks_status     ON tasks(status);
    `);
  }

  // ── Writes ───────────────────────────────────────────────────────────────

  save(task: Task): void {
    this.db
      .prepare(
        `INSERT OR REPLACE INTO tasks
           (id, tenant_id, type, input, status, created_at, updated_at)
         VALUES (?, ?, ?, ?, ?, ?, ?)`
      )
      .run(
        task.id,
        task.tenant_id,
        task.type,
        JSON.stringify(task.input),
        task.status,
        task.created_at,
        task.updated_at
      );
  }

  updateStatus(id: string, status: TaskStatus): Task | undefined {
    const now = new Date().toISOString();
    this.db
      .prepare('UPDATE tasks SET status = ?, updated_at = ? WHERE id = ?')
      .run(status, now, id);
    return this.findById(id);
  }

  delete(id: string): boolean {
    const result = this.db.prepare('DELETE FROM tasks WHERE id = ?').run(id);
    return result.changes > 0;
  }

  // ── Reads ─────────────────────────────────────────────────────────────────

  findById(id: string): Task | undefined {
    const row = this.db
      .prepare('SELECT * FROM tasks WHERE id = ?')
      .get(id) as RawRow | undefined;
    return row ? rowToTask(row) : undefined;
  }

  findByTenant(tenantId: string): Task[] {
    const rows = this.db
      .prepare('SELECT * FROM tasks WHERE tenant_id = ? ORDER BY created_at DESC')
      .all(tenantId) as RawRow[];
    return rows.map(rowToTask);
  }

  /** Close the underlying DB connection (call in tests after each suite). */
  close(): void {
    this.db.close();
  }
}

// ── Helpers ──────────────────────────────────────────────────────────────────

interface RawRow {
  id: string;
  tenant_id: string;
  type: string;
  input: string;
  status: string;
  created_at: string;
  updated_at: string;
}

function rowToTask(row: RawRow): Task {
  return {
    id: row.id,
    tenant_id: row.tenant_id,
    type: row.type as Task['type'],
    input: JSON.parse(row.input) as Record<string, unknown>,
    status: row.status as TaskStatus,
    created_at: row.created_at,
    updated_at: row.updated_at,
  };
}
