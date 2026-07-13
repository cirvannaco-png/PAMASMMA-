import { generateUUID } from '@pamasmma/shared';

export type TaskType = 'content' | 'marketing' | 'social' | 'email';
export type TaskStatus = 'pending' | 'processing' | 'completed' | 'failed' | 'cancelled';

export interface Task {
  id: string;
  tenant_id: string;
  type: TaskType;
  input: Record<string, unknown>;
  created_at: string;
  updated_at: string;
  status: TaskStatus;
}

const VALID_TASK_TYPES: TaskType[] = ['content', 'marketing', 'social', 'email'];

export function isValidTaskType(value: string): value is TaskType {
  return VALID_TASK_TYPES.includes(value as TaskType);
}

// ── Persistence contract ────────────────────────────────────────────────────

/**
 * Storage interface for tasks.
 * Implementations:
 *  - TaskStore:       in-memory Map (tests, local dev with no persistence needed)
 *  - SqliteTaskStore: SQLite-backed (dev/staging, survives restarts)
 */
export interface ITaskStore {
  save(task: Task): void;
  findById(id: string): Task | undefined;
  findByTenant(tenantId: string): Task[];
  updateStatus(id: string, status: TaskStatus): Task | undefined;
  delete(id: string): boolean;
}

// ── Domain services ──────────────────────────────────────────────────────────

export class TaskCreator {
  create(data: { tenant_id: string; type: string; input: unknown }): Task {
    if (!isValidTaskType(data.type)) {
      throw new Error(
        `Invalid task type "${data.type}". Must be one of: ${VALID_TASK_TYPES.join(', ')}`
      );
    }
    const now = new Date().toISOString();
    return {
      id: generateUUID(),
      tenant_id: data.tenant_id,
      type: data.type,
      input: (data.input as Record<string, unknown>) ?? {},
      created_at: now,
      updated_at: now,
      status: 'pending',
    };
  }
}

export class TaskRouter {
  private static readonly routes: Record<TaskType, string> = {
    content: 'content-agent',
    marketing: 'marketing-agent',
    social: 'social-agent',
    email: 'email-agent',
  };

  route(task: Task): string {
    return TaskRouter.routes[task.type] ?? 'default-agent';
  }
}

/** In-memory task store — zero config, data lost on restart. Use for tests. */
export class TaskStore implements ITaskStore {
  private tasks: Map<string, Task> = new Map();

  save(task: Task): void {
    this.tasks.set(task.id, { ...task });
  }

  findById(id: string): Task | undefined {
    const task = this.tasks.get(id);
    return task ? { ...task } : undefined;
  }

  findByTenant(tenantId: string): Task[] {
    return Array.from(this.tasks.values())
      .filter((t) => t.tenant_id === tenantId)
      .map((t) => ({ ...t }));
  }

  updateStatus(id: string, status: TaskStatus): Task | undefined {
    const task = this.tasks.get(id);
    if (!task) return undefined;
    const updated: Task = {
      ...task,
      status,
      updated_at: new Date().toISOString(),
    };
    this.tasks.set(id, updated);
    return { ...updated };
  }

  delete(id: string): boolean {
    return this.tasks.delete(id);
  }
}
