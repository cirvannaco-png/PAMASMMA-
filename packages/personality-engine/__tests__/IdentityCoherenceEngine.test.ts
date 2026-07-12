import { IdentityCoherenceEngine } from '../src/domain/IdentityCoherenceEngine';

describe('IdentityCoherenceEngine', () => {
  let engine: IdentityCoherenceEngine;

  beforeEach(() => {
    engine = new IdentityCoherenceEngine();
  });

  it('returns no warning when vectors are identical', () => {
    const v = [0.5, 0.5, 0.5];
    const report = engine.checkDrift(v, v);
    expect(report.warning).toBe(false);
    expect(report.driftScore).toBe(0);
    expect(report.factors).toHaveLength(0);
  });

  it('returns no warning for small drift (under 0.3 threshold)', () => {
    const report = engine.checkDrift([0.5, 0.5], [0.6, 0.6]);
    expect(report.warning).toBe(false);
    expect(report.driftScore).toBeLessThanOrEqual(0.3);
  });

  it('returns warning for large drift', () => {
    const report = engine.checkDrift([0.1, 0.1], [0.9, 0.9]);
    expect(report.warning).toBe(true);
    expect(report.driftScore).toBeGreaterThan(0.3);
    expect(report.factors.length).toBeGreaterThan(0);
  });

  it('handles empty vectors gracefully', () => {
    const report = engine.checkDrift([], []);
    expect(report.warning).toBe(false);
    expect(report.driftScore).toBe(0);
  });

  it('handles mismatched vector lengths by using the shorter one', () => {
    const report = engine.checkDrift([0.1, 0.2, 0.3], [0.9]);
    expect(report.driftScore).toBeGreaterThan(0);
  });

  it('identifies specific dimension factors', () => {
    const report = engine.checkDrift([0.0], [1.0]);
    expect(report.factors.some((f) => f.startsWith('dimension_0'))).toBe(true);
  });

  it('caps drift score at 1.0', () => {
    const report = engine.checkDrift([0.0, 0.0, 0.0], [1.0, 1.0, 1.0]);
    expect(report.driftScore).toBeLessThanOrEqual(1.0);
  });
});
