import express, { Router } from 'express';
import { OrchestratorAppService } from '../application/orchestratorAppService';

export function orchestratorRoutes(service: OrchestratorAppService): Router {
  const router = express.Router();

  router.post('/task', async (req, res) => {
    try {
      const { tenant_id, type, input } = req.body;
      const taskId = await service.createAndRouteTask(tenant_id, type, input);
      res.json({ task_id: taskId });
    } catch (err: any) {
      res.status(500).json({ error: err.message });
    }
  });

  return router;
}
