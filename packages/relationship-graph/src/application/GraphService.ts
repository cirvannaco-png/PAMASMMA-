import { GraphModel, GraphNode, GraphEdge } from '../domain/GraphModel';

export class GraphService {
  private model = new GraphModel();

  addEntity(
    id: string,
    type: 'agent' | 'task' | 'brand' | 'metric',
    label: string,
    metadata?: Record<string, unknown>
  ): void {
    const node: GraphNode = {
      id,
      type,
      label,
      metadata: metadata || {},
    };
    this.model.addNode(node);
  }

  connectEntities(sourceId: string, targetId: string, relation: string, weight = 1): void {
    const edge: GraphEdge = {
      source: sourceId,
      target: targetId,
      relation,
      weight,
    };
    this.model.addEdge(edge);
  }

  getEntityNetwork(entityId: string): GraphNode[] {
    return this.model.getRelatedNodes(entityId);
  }
}
