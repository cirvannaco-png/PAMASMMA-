import { initTracing } from '@pamasmma/shared';
import { OrchestratorAppService } from './application/orchestratorAppService';
import { TaskCreator, TaskRouter } from './domain/taskManagement';
import { SqliteTaskStore } from './infra/SqliteTaskStore';
import { LocalEventBus } from './infra/LocalEventBus';
import { MemoryManager } from '@pamasmma/memory-core';
import { SqliteLongTermMemory } from '@pamasmma/memory-core';
import { authMiddleware } from './middleware/auth';
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

// Real event bus: delivers events to all subscribers in-process.
// To switch to Kafka, replace LocalEventBus with KafkaProducer here.
const bus = new LocalEventBus();

// SQLite-backed stores: data survives process restarts.
const ltm = new SqliteLongTermMemory();
const taskStore = new SqliteTaskStore();
const memory = new MemoryManager(ltm);

const service = new OrchestratorAppService(
  new TaskCreator(),
  new TaskRouter(),
  taskStore,
  memory,
  bus
);

// Log all events in non-production for observability
if (process.env['NODE_ENV'] !== 'production') {
  bus.subscribe((event) => {
    log('debug', 'event', { type: event.type, tenant_id: event.tenant_id });
  });
}

const app = express();

// Security headers (HSTS, X-Frame-Options, nosniff, etc.)
app.use(helmet());

// Rate limiting — 100 req / 60 s per IP
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

// ── Auth — applied before all routes except /health ────────────────────────
app.use('/api', authMiddleware);

app.use('/api', orchestratorRoutes(service));

// 404 fallback
app.use((_req, res) => {
  res.status(404).json({ error: 'Not found' });
});

// Global Express error handler
app.use(
  (
    err: Error,
    _req: express.Request,
    res: express.Response,
    _next: express.NextFunction
  ) => {
    log('error', 'Unhandled Express error', {
      error: err.message,
      stack: err.stack,
    });
    res.status(500).json({ error: 'Internal server error' });
  }
);

// ── Start ──────────────────────────────────────────────────────────────────
const PORT = process.env['PORT'] ?? 3000;
const server = app.listen(PORT, () =>
  log('info', `Orchestrator running on port ${PORT}`, {
    event_bus: 'LocalEventBus',
    task_store: 'SqliteTaskStore',
    memory_store: 'SqliteLongTermMemory',
    auth: process.env['API_KEYS'] ? 'bearer-token' : 'open (set API_KEYS)',
  })
);

// Graceful shutdown
function shutdown(signal: string): void {
  log('info', `${signal} received — shutting down gracefully`);
  server.close(() => {
    log('info', 'HTTP server closed');
    process.exit(0);
  });
  setTimeout(() => process.exit(1), 10_000).unref();
}

process.on('SIGTERM', () => shutdown('SIGTERM'));
process.on('SIGINT', () => shutdown('SIGINT'));
