import { MarketingIntelService } from './application/MarketingIntelService';
import { marketingApi } from './presentation/marketingApi';
import { MemoryManager } from '@pamasmma/memory-core';
import { IEventBus } from '@pamasmma/shared';
import express from 'express';

export function createMarketingIntel(
  memoryManager: MemoryManager,
  eventBus: IEventBus
) {
  const service = new MarketingIntelService(memoryManager, eventBus);
  const app = express();
  app.use(express.json());
  app.use('/api', marketingApi(service));

  const PORT = process.env.PORT || 3005;
  app.listen(PORT, () => console.log(`Marketing Intel running on port ${PORT}`));

  return { app, service };
}

export { MarketingIntelService };
