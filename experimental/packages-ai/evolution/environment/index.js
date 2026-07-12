// PAMASMMA AI Evolution Layer - Environment Alignment (Milestone 7 Phase 7.5)
// Introduces external signal grounding, environment feedback loop, and objective alignment scaffolding

const { eventBus } = require('../../../kernel/event-bus');
const { evolutionEngine } = require('../core');
const { evolutionMemory } = require('../memory');
const { evolutionStabilization } = require('../stabilization');

/**
 * This layer introduces contact with "outside signals".
 * Not truth. Not reality. Just constraints that approximate it.
 */
class EnvironmentAlignment {
  constructor() {
    this.externalSignals = [];
    this.alignmentHistory = [];
    this.noiseTolerance = 0.35;
  }

  /**
   * Inject external environment signals (metrics, rewards, constraints)
   */
  ingestSignals(signals = []) {
    this.externalSignals = signals;

    eventBus.emit('evolution:environment:signals_ingested', {
      count: signals.length,
      timestamp: Date.now()
    });
  }

  /**
   * Compute alignment score between agent output and external signal
   */
  _alignmentScore(agentOutput, signal) {
    // simplified similarity heuristic (placeholder for real embedding similarity)
    const a = JSON.stringify(agentOutput || {}).length;
    const b = JSON.stringify(signal || {}).length;

    const diff = Math.abs(a - b);
    const norm = Math.max(a, b, 1);

    return 1 - Math.min(1, diff / norm);
  }

  /**
   * Evaluate system alignment against external environment
   */
  evaluate(state = {}) {
    const agents = Array.from(evolutionEngine.agents.entries());

    if (!this.externalSignals.length || !agents.length) {
      return { alignment: 0, status: 'insufficient_data' };
    }

    let totalScore = 0;
    let comparisons = 0;

    for (const [name, agent] of agents) {
      const memoryScore = evolutionMemory.scores.get(name) || 1;

      const output = {
        weight: agent.weight,
        memory: memoryScore,
        state
      };

      for (const signal of this.externalSignals) {
        totalScore += this._alignmentScore(output, signal);
        comparisons++;
      }
    }

    const alignment = comparisons > 0 ? totalScore / comparisons : 0;

    const result = {
      alignment,
      timestamp: Date.now(),
      externalSignals: this.externalSignals.length
    };

    this.alignmentHistory.push(result);

    eventBus.emit('evolution:environment:alignment_evaluated', result);

    return result;
  }

  /**
   * Apply corrective pressure to evolution based on alignment
   */
  applyAlignmentPressure() {
    const latest = this.alignmentHistory[this.alignmentHistory.length - 1];
    if (!latest) return;

    const adjustment = latest.alignment < this.noiseTolerance ? -0.05 : 0.02;

    for (const [name, agent] of evolutionEngine.agents.entries()) {
      const mem = evolutionMemory.scores.get(name) || 1;

      const adjusted = mem + adjustment;
      evolutionMemory.scores.set(name, Math.max(0.1, adjusted));
    }

    eventBus.emit('evolution:environment:pressure_applied', {
      adjustment,
      alignment: latest.alignment
    });
  }

  /**
   * Snapshot of environment state
   */
  snapshot() {
    return {
      signals: this.externalSignals.length,
      lastAlignment: this.alignmentHistory[this.alignmentHistory.length - 1] || null
    };
  }
}

const environmentAlignment = new EnvironmentAlignment();

module.exports = { EnvironmentAlignment, environmentAlignment };