export interface DriftReport {
  warning: boolean;
  driftScore: number;
  factors: string[];
}

/**
 * Measures personality drift between a baseline and current behaviour vector.
 * Vectors are arrays of numeric scores (0–1) representing personality dimensions.
 */
export class IdentityCoherenceEngine {
  checkDrift(baseline: number[], current: number[]): DriftReport {
    if (!baseline || !current || baseline.length === 0 || current.length === 0) {
      return { warning: false, driftScore: 0, factors: [] };
    }

    const driftScore = this.calculateDrift(baseline, current);
    const warning = driftScore > 0.3;
    const factors = warning ? this.identifyFactors(baseline, current) : [];

    return { warning, driftScore, factors };
  }

  private calculateDrift(baseline: number[], current: number[]): number {
    const len = Math.min(baseline.length, current.length);
    let totalDelta = 0;

    for (let i = 0; i < len; i++) {
      totalDelta += Math.abs(baseline[i] - current[i]);
    }

    return Math.min(totalDelta / len, 1);
  }

  private identifyFactors(baseline: number[], current: number[]): string[] {
    const factors: string[] = [];
    const len = Math.min(baseline.length, current.length);

    for (let i = 0; i < len; i++) {
      const delta = Math.abs(baseline[i] - current[i]);
      if (delta > 0.3) {
        factors.push(`dimension_${i}_shift_${delta.toFixed(2)}`);
      }
    }

    if (factors.length === 0) {
      factors.push('personality_shift_detected');
    }

    return factors;
  }
}
