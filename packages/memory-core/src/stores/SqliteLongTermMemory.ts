import Database from 'better-sqlite3';
import { EpisodicRecord, SemanticFact } from '../types';
import { ILongTermMemory } from './ILongTermMemory';

/**
 * SQLite-backed long-term memory store.
 *
 * Why SQLite?
 *  - Zero infrastructure: no separate database process to run.
 *  - Synchronous API (better-sqlite3): no async/await noise in callers.
 *  - Survives process restarts — episodic and semantic records persist.
 *  - Easy to inspect with any SQLite browser during development.
 *
 * In production, swap this for a Postgres adapter that implements ILongTermMemory.
 * Pass ':memory:' as dbPath in tests for an in-process, zero-cleanup database.
 */
export class SqliteLongTermMemory implements ILongTermMemory {
  private readonly db: Database.Database;

  constructor(dbPath: string = process.env['DATABASE_PATH'] ?? './pamasmma.db') {
    this.db = new Database(dbPath);
    this.migrate();
  }

  // ── Schema ──────────────────────────────────────────────────────────────

  private migrate(): void {
    this.db.exec(`
      CREATE TABLE IF NOT EXISTS episodic_records (
        key        TEXT PRIMARY KEY,
        tenant_id  TEXT NOT NULL,
        record     TEXT NOT NULL
      );

      CREATE TABLE IF NOT EXISTS semantic_facts (
        key        TEXT PRIMARY KEY,
        tenant_id  TEXT NOT NULL,
        fact       TEXT NOT NULL
      );

      CREATE INDEX IF NOT EXISTS idx_episodic_tenant ON episodic_records(tenant_id);
      CREATE INDEX IF NOT EXISTS idx_semantic_tenant  ON semantic_facts(tenant_id);
    `);
  }

  // ── Episodic ────────────────────────────────────────────────────────────

  storeEpisodic(record: EpisodicRecord): void {
    const key = `${record.tenant_id ?? ''}:${record.id}`;
    this.db
      .prepare(
        `INSERT OR REPLACE INTO episodic_records (key, tenant_id, record)
         VALUES (?, ?, ?)`
      )
      .run(key, record.tenant_id ?? '', JSON.stringify(record));
  }

  getEpisodic(tenantId: string, taskId: string): EpisodicRecord | undefined {
    const key = `${tenantId}:${taskId}`;
    const row = this.db
      .prepare('SELECT record FROM episodic_records WHERE key = ?')
      .get(key) as { record: string } | undefined;
    return row ? (JSON.parse(row.record) as EpisodicRecord) : undefined;
  }

  // ── Semantic ─────────────────────────────────────────────────────────────

  storeSemantic(fact: SemanticFact): void {
    const key = `${fact.tenant_id ?? ''}:${fact.id}`;
    this.db
      .prepare(
        `INSERT OR REPLACE INTO semantic_facts (key, tenant_id, fact)
         VALUES (?, ?, ?)`
      )
      .run(key, fact.tenant_id ?? '', JSON.stringify(fact));
  }

  getSemantic(tenantId: string, factId: string): SemanticFact | undefined {
    const key = `${tenantId}:${factId}`;
    const row = this.db
      .prepare('SELECT fact FROM semantic_facts WHERE key = ?')
      .get(key) as { fact: string } | undefined;
    return row ? (JSON.parse(row.fact) as SemanticFact) : undefined;
  }

  /** Close the underlying database connection (call in tests after each suite). */
  close(): void {
    this.db.close();
  }
}
