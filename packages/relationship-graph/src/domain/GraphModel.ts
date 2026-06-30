export interface GraphNode {
  id: string;
  type: 'agent' | 'task' | 'brand' | 'metric';
  label: string;
  metadata: Record<string, unknown>;
}

export interface GraphEdge {
  source: string;
  target: string;
  relation: string;
  weight: number;
}

export class GraphModel {
  private nodes: Map<string, GraphNode> = new Map();
  private edges: Map<string, GraphEdge> = new Map();

  addNode(node: GraphNode): void {
    this.nodes.set(node.id, node);
  }

  addEdge(edge: GraphEdge): void {
    const key = `${edge.source}:${edge.target}`;
    this.edges.set(key, edge);
  }

  getRelatedNodes(nodeId: string): GraphNode[] {
    const related: GraphNode[] = [];
    for (const edge of this.edges.values()) {
      if (edge.source === nodeId && this.nodes.has(edge.target)) {
        related.push(this.nodes.get(edge.target)!);
      }
    }
    return related;
  }
}
