import { initTracing } from '@pamasmma/shared';
import { OrchestratorAppService } from './application/orchestratorAppService';
import { TaskCreator, TaskRouter, TaskStore } from './domain/taskManagement';
import { MemoryManager } from '@pamasmma/memory-core';
import { KafkaProducer } from './infra/KafkaProducer';
import express from 'express';
import helmet from 'helmet';
import rateLimit from 'express-rate-limit';
import { orchestratorRoutes } from './presentation/routes';

// ── Global error guards ────────────────────────────────────────────────────
process.on('unhandledRejection', (reason: unknown) => {
  log('fatal', 'Unhandled promise rejection', { reason: String(reason) });
  process.exit(1);
});

process.on('uncaughtException', (err: Error) => {
  log('fatal', 'Uncaught exception', { error: err.message, stack: err.stack });
  process.exit(1);
});

// ── Structured logger ──────────────────────────────────────────────────────
function log(level: string, msg: string, extra?: Record<string, unknown>): void {
  console.log(JSON.stringify({ level, msg, ...extra, ts: new Date().toISOString() }));
}

// ── Bootstrap ──────────────────────────────────────────────────────────────
initTracing('orchestrator');

const bus = new KafkaProducer();
const memory = new MemoryManager();
const taskStore = new TaskStore();

const service = new OrchestratorAppService(
  new TaskCreator(),
  new TaskRouter(),
  taskStore,
  memory,
  bus
);

const app = express();

// Security headers (HSTS, X-Frame-Options, etc.)
app.use(helmet());

// Rate limiting — 100 req / min per IP
app.use(
  rateLimit({
    windowMs: 60_000,
    max: 100,
    standardHeaders: true,
    legacyHeaders: false,
    message: { error: 'Too many requests, please try again later.' },
  })
);

app.use(express.json({ limit: '1mb' }));
app.use('/api', orchestratorRoutes(service));

// 404 fallback
app.use((_req, res) => {
  res.status(404).json({ error: 'Not found' });
});

// Global Express error handler
app.use((err: Error, _req: express.Request, res: express.Response, _next: express.NextFunction) => {
  log('error', 'Unhandled Express error', { error: err.message, stack: err.stack });
  res.status(500).json({ error: 'Internal server error' });
});

// ── Start ──────────────────────────────────────────────────────────────────
const PORT = process.env['PORT'] ?? 3000;
const server = app.listen(PORT, () =>
  log('info', `Orchestrator running on port ${PORT}`)
);

// Graceful shutdown
function shutdown(signal: string): void {
  log('info', `${signal} received — shutting down gracefully`);
  server.close(() => {
    log('info', 'HTTP server closed');
    process.exit(0);
  });
  // Force exit after 10 s if connections don't drain
  setTimeout(() => process.exit(1), 10_000).unref();
}

process.on('SIGTERM', () => shutdown('SIGTERM'));
process.on('SIGINT', () => shutdown('SIGINT'));
