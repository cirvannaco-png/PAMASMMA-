import { IEventBus } from '@pamasmma/shared';
import { Task, TaskCreator, TaskRouter, ITaskStore, TaskStatus } from '../domain/taskManagement';
import { MemoryManager } from '@pamasmma/memory-core';

export class OrchestratorAppService {
  constructor(
    private taskCreator: TaskCreator,
    private taskRouter: TaskRouter,
    private taskStore: ITaskStore,
    private memoryManager: MemoryManager,
    private eventBus: IEventBus
  ) {}

  async createAndRouteTask(
    tenantId: string,
    type: string,
    input: unknown
  ): Promise<string> {
    const task = this.taskCreator.create({ tenant_id: tenantId, type, input });

    this.taskStore.save(task);

    await this.memoryManager.writeMemory(
      {
        type: 'episodic',
        id: task.id,
        data: task as unknown as Record<string, unknown>,
        timestamp: new Date().toISOString(),
      },
      { source: 'domain', tenant_id: tenantId, task_id: task.id }
    );

    this.taskRouter.route(task);

    await this.eventBus.emit({
      type: 'task.created',
      schema_version: 1,
      timestamp: new Date().toISOString(),
      tenant_id: tenantId,
      task_id: task.id,
      task_type: task.type,
      input: task.input,
    });

    // Mark as processing after routing
    this.taskStore.updateStatus(task.id, 'processing');

    return task.id;
  }

  getTask(tenantId: string, taskId: string): Task | undefined {
    const task = this.taskStore.findById(taskId);
    if (!task || task.tenant_id !== tenantId) return undefined;
    return task;
  }

  listTasks(tenantId: string): Task[] {
    return this.taskStore.findByTenant(tenantId);
  }

  updateTaskStatus(
    tenantId: string,
    taskId: string,
    status: TaskStatus
  ): Task | undefined {
    const task = this.taskStore.findById(taskId);
    if (!task || task.tenant_id !== tenantId) return undefined;
    return this.taskStore.updateStatus(taskId, status);
  }

  cancelTask(tenantId: string, taskId: string): boolean {
    const task = this.taskStore.findById(taskId);
    if (!task || task.tenant_id !== tenantId) return false;
    this.taskStore.updateStatus(taskId, 'cancelled');
    return true;
  }
}
