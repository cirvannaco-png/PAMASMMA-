import { GraphService } from './application/GraphService';
import { graphApi } from './presentation/graphApi';
import express from 'express';

export function createRelationshipGraph() {
  const service = new GraphService();
  const app = express();
  app.use(express.json());
  app.use('/api', graphApi(service));

  const PORT = process.env.PORT || 3006;
  app.listen(PORT, () => console.log(`Relationship Graph running on port ${PORT}`));

  return { app, service };
}

export { GraphService };
