import { initTracing } from '@pamasmma/shared';
import { OrchestratorAppService } from './application/orchestratorAppService';
import { TaskCreator, TaskRouter } from './domain/taskManagement';
import { MemoryManager } from '@pamasmma/memory-core';
import { KafkaProducer } from './infra/KafkaProducer';
import express from 'express';
import { orchestratorRoutes } from './presentation/routes';

initTracing('orchestrator');

const bus = new KafkaProducer();
const memory = new MemoryManager();
const service = new OrchestratorAppService(new TaskCreator(), new TaskRouter(), memory, bus);

const app = express();
app.use(express.json());
app.use('/api', orchestratorRoutes(service));

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log(`Orchestrator running on port ${PORT}`));
