// PAMASMMA AI Evolution Layer - Semantic Truth & Constraint Reasoning (Milestone 8.4)
// Introduces contradiction resolution, semantic consistency, dependency reasoning, and truth-weighted coherence

const { eventBus } = require('../../../../kernel/event-bus');
const { worldModel } = require('../../world');
const { invariantEngine } = require('../invariants');
const { causalValidator } = require('../../causal');
const { probabilisticForecastEngine } = require('../../probabilistic');

/**
 * This layer does NOT compute truth.
 * It evaluates coherence between competing internal representations of truth.
 */
class SemanticTruthEngine {
  constructor() {
    this.conflictGraph = new Map();
    this.resolutionHistory = [];
    this.semanticWeights = new Map();
  }

  /**
   * Build contradiction graph from system state
   */
  detectContradictions() {
    const violations = invariantEngine.violations || [];
    const contradictions = [];

    for (const v of violations) {
      contradictions.push({
        id: `contr_${Date.now()}_${Math.random().toString(16).slice(2)}`,
        source: v.id,
        severity: this._computeSeverity(v)
      });
    }

    this.conflictGraph.set(Date.now(), contradictions);

    eventBus.emit('semantic:contradictions_detected', contradictions);

    return contradictions;
  }

  /**
   * Compute severity of contradiction (weighted impact model)
   */
  _computeSeverity(violation) {
    let base = 0.5;

    if (violation.id?.includes('decision')) base += 0.2;
    if (violation.id?.includes('causal')) base += 0.2;
    if (violation.id?.includes('confidence')) base += 0.1;

    return Math.min(1, base);
  }

  /**
   * Resolve contradictions using weighted suppression (not deletion)
   */
  resolve() {
    const latest = Array.from(this.conflictGraph.values()).slice(-1)[0] || [];

    const resolved = latest.map(c => ({
      id: c.id,
      resolution: c.severity > 0.7 ? 'priority_override' : 'balanced_decay',
      adjustedWeight: 1 - c.severity * 0.5
    }));

    this.resolutionHistory.push({
      timestamp: Date.now(),
      resolved
    });

    eventBus.emit('semantic:resolution_complete', resolved);

    return resolved;
  }

  /**
   * Compute semantic coherence score across system layers
   */
  coherenceScore() {
    const violations = invariantEngine.violations?.length || 0;
    const contradictions = Array.from(this.conflictGraph.values()).flat().length;

    const causal = causalValidator.accuracy?.() || 0;
    const confidence = Array.from(probabilisticForecastEngine.beliefs?.values?.() || [])
      .reduce((a, b) => a + (b.confidence || 0), 0);

    const normalizedConfidence = confidence ? confidence / Math.max(1, probabilisticForecastEngine.beliefs.size) : 0;

    const score = (
      (1 - Math.min(1, violations * 0.1)) * 0.3 +
      (1 - Math.min(1, contradictions * 0.05)) * 0.3 +
      causal * 0.2 +
      normalizedConfidence * 0.2
    );

    return Math.max(0, Math.min(1, score));
  }

  /**
   * Snapshot semantic layer
   */
  snapshot() {
    return {
      conflicts: Array.from(this.conflictGraph.values()).flat().length,
      resolutions: this.resolutionHistory.length,
      coherence: this.coherenceScore()
    };
  }
}

const semanticTruthEngine = new SemanticTruthEngine();

module.exports = { SemanticTruthEngine, semanticTruthEngine };