import express, { Router, Request, Response } from 'express';
import { OrchestratorAppService } from '../application/orchestratorAppService';
import { isValidTaskType, TaskStatus } from '../domain/taskManagement';

const VALID_STATUSES: TaskStatus[] = [
  'pending',
  'processing',
  'completed',
  'failed',
  'cancelled',
];

function isValidStatus(value: string): value is TaskStatus {
  return VALID_STATUSES.includes(value as TaskStatus);
}

export function orchestratorRoutes(service: OrchestratorAppService): Router {
  const router = express.Router();

  /** Health check */
  router.get('/health', (_req: Request, res: Response) => {
    res.json({ status: 'ok', service: 'orchestrator', ts: new Date().toISOString() });
  });

  /** Create a task */
  router.post('/task', async (req: Request, res: Response) => {
    const { tenant_id, type, input } = req.body ?? {};

    if (!tenant_id || typeof tenant_id !== 'string') {
      return res.status(400).json({ error: 'tenant_id is required and must be a string' });
    }
    if (!type || typeof type !== 'string') {
      return res.status(400).json({ error: 'type is required and must be a string' });
    }
    if (!isValidTaskType(type)) {
      return res.status(400).json({
        error: `Invalid type "${type}". Allowed: content, marketing, social, email`,
      });
    }

    try {
      const taskId = await service.createAndRouteTask(tenant_id, type, input ?? {});
      return res.status(201).json({ task_id: taskId });
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Internal error';
      return res.status(500).json({ error: message });
    }
  });

  /** List all tasks for a tenant */
  router.get('/tasks', (req: Request, res: Response) => {
    const tenantId = req.query['tenant_id'];
    if (!tenantId || typeof tenantId !== 'string') {
      return res.status(400).json({ error: 'tenant_id query param is required' });
    }
    const tasks = service.listTasks(tenantId);
    return res.json({ tasks, count: tasks.length });
  });

  /** Get a single task by ID */
  router.get('/task/:id', (req: Request, res: Response) => {
    const tenantId = req.query['tenant_id'];
    if (!tenantId || typeof tenantId !== 'string') {
      return res.status(400).json({ error: 'tenant_id query param is required' });
    }
    const task = service.getTask(tenantId, req.params['id'] ?? '');
    if (!task) {
      return res.status(404).json({ error: 'Task not found' });
    }
    return res.json(task);
  });

  /** Update task status */
  router.patch('/task/:id/status', (req: Request, res: Response) => {
    const { tenant_id, status } = req.body ?? {};

    if (!tenant_id || typeof tenant_id !== 'string') {
      return res.status(400).json({ error: 'tenant_id is required' });
    }
    if (!status || typeof status !== 'string') {
      return res.status(400).json({ error: 'status is required' });
    }
    if (!isValidStatus(status)) {
      return res.status(400).json({
        error: `Invalid status "${status}". Allowed: ${VALID_STATUSES.join(', ')}`,
      });
    }

    const updated = service.updateTaskStatus(tenant_id, req.params['id'] ?? '', status);
    if (!updated) {
      return res.status(404).json({ error: 'Task not found' });
    }
    return res.json(updated);
  });

  /** Cancel a task */
  router.delete('/task/:id', (req: Request, res: Response) => {
    const tenantId = req.query['tenant_id'];
    if (!tenantId || typeof tenantId !== 'string') {
      return res.status(400).json({ error: 'tenant_id query param is required' });
    }
    const cancelled = service.cancelTask(tenantId, req.params['id'] ?? '');
    if (!cancelled) {
      return res.status(404).json({ error: 'Task not found' });
    }
    return res.json({ cancelled: true, task_id: req.params['id'] });
  });

  return router;
}
