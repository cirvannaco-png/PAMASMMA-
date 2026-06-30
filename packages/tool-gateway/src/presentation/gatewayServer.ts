import express, { Router } from 'express';
import { ToolExecutionService } from '../application/ToolExecutionService';
import { requestLatencyHistogram } from '@pamasmma/shared';

export function gatewayServer(service: ToolExecutionService): express.Application {
  const app = express();
  app.use(express.json());

  app.post('/execute', async (req, res) => {
    const start = Date.now();
    try {
      const { tool_name, inputs, tenant_id, task_id, trace_id } = req.body;
      const result = await service.execute(tool_name, inputs, { tenant_id, task_id, trace_id });
      
      const latency = (Date.now() - start) / 1000;
      requestLatencyHistogram.labels('tool-gateway', '/execute').observe(latency);

      if (result.ok) {
        res.json({ success: true, data: result.value });
      } else {
        res.status(result.error.statusCode).json({ error: result.error.message });
      }
    } catch (err: any) {
      res.status(500).json({ error: err.message });
    }
  });

  app.get('/metrics', (req, res) => {
    res.set('Content-Type', 'text/plain');
    // In production: use prom-client registry.metrics()
    res.send('Prometheus metrics endpoint');
  });

  return app;
}
