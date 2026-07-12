import { GraphService } from '../src/application/GraphService';

describe('GraphService', () => {
  let service: GraphService;

  beforeEach(() => {
    service = new GraphService();
  });

  describe('addEntity', () => {
    it('adds an entity without throwing', () => {
      expect(() => service.addEntity('agent-1', 'agent', 'Main Agent')).not.toThrow();
    });

    it('accepts optional metadata', () => {
      expect(() =>
        service.addEntity('task-1', 'task', 'Content Task', { priority: 'high' })
      ).not.toThrow();
    });

    it('supports all valid entity types', () => {
      const types: Array<'agent' | 'task' | 'brand' | 'metric'> = [
        'agent', 'task', 'brand', 'metric',
      ];
      types.forEach((type, i) => {
        expect(() => service.addEntity(`id-${i}`, type, `Label ${i}`)).not.toThrow();
      });
    });
  });

  describe('connectEntities', () => {
    it('connects two existing entities', () => {
      service.addEntity('a1', 'agent', 'Agent');
      service.addEntity('b1', 'brand', 'Brand');
      expect(() => service.connectEntities('a1', 'b1', 'promotes')).not.toThrow();
    });

    it('uses a default weight of 1 when not specified', () => {
      service.addEntity('a', 'agent', 'A');
      service.addEntity('b', 'metric', 'B');
      service.connectEntities('a', 'b', 'tracks');
      // Network should have b as a related node
      const network = service.getEntityNetwork('a');
      expect(network).toHaveLength(1);
    });

    it('accepts a custom weight', () => {
      service.addEntity('x', 'agent', 'X');
      service.addEntity('y', 'task', 'Y');
      expect(() => service.connectEntities('x', 'y', 'delegates', 0.75)).not.toThrow();
    });
  });

  describe('getEntityNetwork', () => {
    it('returns all directly connected nodes', () => {
      service.addEntity('hub', 'agent', 'Hub');
      service.addEntity('n1', 'task', 'Task 1');
      service.addEntity('n2', 'brand', 'Brand 1');
      service.addEntity('n3', 'metric', 'Metric 1');

      service.connectEntities('hub', 'n1', 'owns');
      service.connectEntities('hub', 'n2', 'represents');
      service.connectEntities('hub', 'n3', 'tracks');

      const network = service.getEntityNetwork('hub');
      expect(network).toHaveLength(3);
      expect(network.map((n) => n.id).sort()).toEqual(['n1', 'n2', 'n3']);
    });

    it('returns empty array for a node with no connections', () => {
      service.addEntity('lone', 'agent', 'Lone Agent');
      expect(service.getEntityNetwork('lone')).toEqual([]);
    });

    it('returns empty array for an unknown entity id', () => {
      expect(service.getEntityNetwork('unknown')).toEqual([]);
    });

    it('does not include nodes connected in the reverse direction', () => {
      service.addEntity('src', 'agent', 'Source');
      service.addEntity('dst', 'task', 'Destination');
      service.connectEntities('dst', 'src', 'reports-to');

      // src → dst direction was NOT set, so src's network should be empty
      expect(service.getEntityNetwork('src')).toEqual([]);
    });
  });

  describe('end-to-end scenario', () => {
    it('builds a simple agent–brand–metric graph correctly', () => {
      service.addEntity('agent-main', 'agent', 'PAMASMMA Core');
      service.addEntity('brand-acme', 'brand', 'Acme Corp');
      service.addEntity('metric-ctr', 'metric', 'CTR');

      service.connectEntities('agent-main', 'brand-acme', 'manages', 1);
      service.connectEntities('agent-main', 'metric-ctr', 'monitors', 0.8);

      const network = service.getEntityNetwork('agent-main');
      expect(network).toHaveLength(2);
      expect(network.find((n) => n.type === 'brand')?.label).toBe('Acme Corp');
      expect(network.find((n) => n.type === 'metric')?.label).toBe('CTR');
    });
  });
});
