import express from 'express';
import { MarketingIntelService } from '../application/MarketingIntelService';

export function marketingApi(service: MarketingIntelService) {
  const router = express.Router();

  router.post('/analyze', async (req, res) => {
    try {
      const { tenant_id, task_id, decision } = req.body as {
        tenant_id?: string;
        task_id?: string;
        decision?: Record<string, unknown>;
      };

      if (!tenant_id || typeof tenant_id !== 'string') {
        res.status(400).json({ error: 'tenant_id is required' });
        return;
      }
      if (!task_id || typeof task_id !== 'string') {
        res.status(400).json({ error: 'task_id is required' });
        return;
      }
      if (!decision || typeof decision !== 'object') {
        res.status(400).json({ error: 'decision object is required' });
        return;
      }

      const result = await service.analyzeMarketingDecision(tenant_id, task_id, decision);
      res.json(result);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Unknown error';
      res.status(500).json({ error: message });
    }
  });

  return router;
}
