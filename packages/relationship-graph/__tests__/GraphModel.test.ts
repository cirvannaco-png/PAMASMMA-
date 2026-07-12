import { GraphModel, GraphNode, GraphEdge } from '../src/domain/GraphModel';

function makeNode(overrides: Partial<GraphNode> = {}): GraphNode {
  return {
    id: 'node-1',
    type: 'agent',
    label: 'Test Agent',
    metadata: {},
    ...overrides,
  };
}

function makeEdge(overrides: Partial<GraphEdge> = {}): GraphEdge {
  return {
    source: 'node-1',
    target: 'node-2',
    relation: 'manages',
    weight: 1,
    ...overrides,
  };
}

describe('GraphModel', () => {
  let model: GraphModel;

  beforeEach(() => {
    model = new GraphModel();
  });

  describe('addNode / getRelatedNodes', () => {
    it('stores nodes and returns related nodes via edges', () => {
      model.addNode(makeNode({ id: 'a', label: 'Agent A' }));
      model.addNode(makeNode({ id: 'b', label: 'Brand B', type: 'brand' }));
      model.addEdge(makeEdge({ source: 'a', target: 'b', relation: 'promotes' }));

      const related = model.getRelatedNodes('a');
      expect(related).toHaveLength(1);
      expect(related[0].id).toBe('b');
    });

    it('returns empty array when a node has no outgoing edges', () => {
      model.addNode(makeNode({ id: 'isolated' }));
      expect(model.getRelatedNodes('isolated')).toEqual([]);
    });

    it('returns empty array when querying a node not in the graph', () => {
      expect(model.getRelatedNodes('ghost')).toEqual([]);
    });

    it('does not return a related node if the target node is not in the graph', () => {
      model.addNode(makeNode({ id: 'src' }));
      // Edge points to 'ghost' which was never added
      model.addEdge(makeEdge({ source: 'src', target: 'ghost' }));
      expect(model.getRelatedNodes('src')).toEqual([]);
    });

    it('overwrites a node with the same id', () => {
      model.addNode(makeNode({ id: 'n1', label: 'First' }));
      model.addNode(makeNode({ id: 'n1', label: 'Second' }));
      // If n1 is related from another node, it should reflect the latest value
      model.addNode(makeNode({ id: 'parent' }));
      model.addEdge(makeEdge({ source: 'parent', target: 'n1' }));
      const related = model.getRelatedNodes('parent');
      expect(related[0].label).toBe('Second');
    });
  });

  describe('addEdge', () => {
    it('overwrites an edge with the same source:target key', () => {
      model.addNode(makeNode({ id: 'a' }));
      model.addNode(makeNode({ id: 'b' }));
      model.addEdge(makeEdge({ source: 'a', target: 'b', relation: 'old', weight: 0.5 }));
      model.addEdge(makeEdge({ source: 'a', target: 'b', relation: 'new', weight: 0.9 }));

      // Still only one relation
      const related = model.getRelatedNodes('a');
      expect(related).toHaveLength(1);
    });

    it('supports multiple outgoing edges from one node', () => {
      model.addNode(makeNode({ id: 'hub' }));
      model.addNode(makeNode({ id: 'x' }));
      model.addNode(makeNode({ id: 'y' }));
      model.addEdge(makeEdge({ source: 'hub', target: 'x' }));
      model.addEdge(makeEdge({ source: 'hub', target: 'y' }));

      const related = model.getRelatedNodes('hub');
      expect(related).toHaveLength(2);
      expect(related.map((n) => n.id).sort()).toEqual(['x', 'y']);
    });

    it('supports all node types', () => {
      const types: GraphNode['type'][] = ['agent', 'task', 'brand', 'metric'];
      types.forEach((type, i) => {
        model.addNode(makeNode({ id: `n${i}`, type }));
      });
      model.addEdge(makeEdge({ source: 'n0', target: 'n1' }));
      model.addEdge(makeEdge({ source: 'n0', target: 'n2' }));
      expect(model.getRelatedNodes('n0')).toHaveLength(2);
    });
  });
});
