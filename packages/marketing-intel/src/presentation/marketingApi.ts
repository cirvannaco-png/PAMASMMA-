import express from 'express';
import { MarketingIntelService } from '../application/MarketingIntelService';

export function marketingApi(service: MarketingIntelService) {
  const router = express.Router();

  router.post('/analyze', async (req, res) => {
    try {
      const { tenant_id, task_id, decision } = req.body;
      const result = await service.analyzeMarketingDecision(tenant_id, task_id, decision);
      res.json(result);
    } catch (err: any) {
      res.status(500).json({ error: err.message });
    }
  });

  return router;
}
