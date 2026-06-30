import express from 'express';
import { GraphService } from '../application/GraphService';

export function graphApi(service: GraphService) {
  const router = express.Router();

  router.post('/entity', (req, res) => {
    try {
      const { id, type, label, metadata } = req.body;
      service.addEntity(id, type, label, metadata);
      res.json({ success: true });
    } catch (err: any) {
      res.status(500).json({ error: err.message });
    }
  });

  router.post('/connect', (req, res) => {
    try {
      const { source_id, target_id, relation, weight } = req.body;
      service.connectEntities(source_id, target_id, relation, weight);
      res.json({ success: true });
    } catch (err: any) {
      res.status(500).json({ error: err.message });
    }
  });

  router.get('/network/:entityId', (req, res) => {
    try {
      const network = service.getEntityNetwork(req.params.entityId);
      res.json({ entities: network });
    } catch (err: any) {
      res.status(500).json({ error: err.message });
    }
  });

  return router;
}
