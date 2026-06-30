import { Registry, collectDefaultMetrics, Counter, Histogram } from 'prom-client';

export const registry = new Registry();
collectDefaultMetrics({ register: registry });

export const requestLatencyHistogram = new Histogram({
  name: 'http_request_duration_seconds',
  help: 'Request latency in seconds',
  labelNames: ['service', 'route'],
  registers: [registry],
});

export const injectionAttemptsCounter = new Counter({
  name: 'injection_attempts_total',
  help: 'Total number of prompt injection attempts detected',
  registers: [registry],
});

export const maliBlockCounter = new Counter({
  name: 'mali_block_total',
  help: 'Total blocked by Mali',
  registers: [registry],
});

export const driftWarningCounter = new Counter({
  name: 'agent_drift_warnings_total',
  help: 'Number of drift warnings',
  registers: [registry],
});