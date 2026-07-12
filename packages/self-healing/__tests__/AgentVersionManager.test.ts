import { AgentVersionManager } from '../src/AgentVersionManager';

describe('AgentVersionManager', () => {
  let manager: AgentVersionManager;

  beforeEach(() => {
    manager = new AgentVersionManager();
  });

  it('saves a version and retrieves it', () => {
    const v = manager.saveVersion('agent-1', 'abc123');
    expect(v.promptHash).toBe('abc123');
    expect(v.version).toBeDefined();
    expect(v.isStable).toBe(false);
    expect(v.createdAt).toBeDefined();
  });

  it('returns undefined for stable version when none is marked', () => {
    manager.saveVersion('agent-1', 'abc123');
    expect(manager.getStableVersion('agent-1')).toBeUndefined();
  });

  it('marks a version as stable', () => {
    const v = manager.saveVersion('agent-1', 'abc123');
    manager.markAsStable('agent-1', v.version);

    const stable = manager.getStableVersion('agent-1');
    expect(stable).toBeDefined();
    expect(stable?.promptHash).toBe('abc123');
    expect(stable?.isStable).toBe(true);
  });

  it('only one version is stable at a time', () => {
    const v1 = manager.saveVersion('agent-1', 'hash-1');
    const v2 = manager.saveVersion('agent-1', 'hash-2');

    manager.markAsStable('agent-1', v1.version);
    manager.markAsStable('agent-1', v2.version);

    const stable = manager.getStableVersion('agent-1');
    expect(stable?.promptHash).toBe('hash-2');
  });

  it('returns undefined for unknown agent', () => {
    expect(manager.getStableVersion('ghost-agent')).toBeUndefined();
  });

  it('isolates versions per agent', () => {
    manager.saveVersion('agent-a', 'hash-a');
    const vb = manager.saveVersion('agent-b', 'hash-b');
    manager.markAsStable('agent-b', vb.version);

    expect(manager.getStableVersion('agent-a')).toBeUndefined();
    expect(manager.getStableVersion('agent-b')).toBeDefined();
  });
});
