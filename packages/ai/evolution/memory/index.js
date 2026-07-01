// PAMASMMA AI Evolution Layer - Memory Driven Adaptation (Milestone 7 Phase 7.2)
// Adds persistence of agent performance + adaptive weight mutation (controlled reinforcement)

const { eventBus } = require('../../../kernel/event-bus');
const { evolutionEngine } = require('../core');

/**
 * Memory model:
 * Stores historical agent outputs and adjusts influence weights over time.
 * This is NOT general learning—this is constrained reinforcement scoring.
 */
class EvolutionMemory {
  constructor() {
    this.history = [];
    this.scores = new Map(); // agent -> performance score
    this.learningRate = 0.05;
  }

  /**
   * Record a tick result from evolution engine
   */
  recordTick(tickResult) {
    this.history.push(tickResult);

    const { outputs = [] } = tickResult;

    for (const o of outputs) {
      const prev = this.scores.get(o.name) || 1;

      // heuristic reward: higher weight outputs are assumed more valuable
      const reward = (o.weight || 1) * (o.result ? 1 : 0.5);

      const updated = prev + this.learningRate * (reward - prev);

      this.scores.set(o.name, updated);
    }

    eventBus.emit('evolution:memory_updated', {
      agents: Array.from(this.scores.entries())
    });
  }

  /**
   * Apply learned weights back into evolution engine
   */
  applyLearning() {
    for (const [name, score] of this.scores.entries()) {
      const agent = evolutionEngine.agents.get(name);

      if (agent) {
        agent.weight = Math.max(0.1, Math.min(5, score));
      }
    }

    eventBus.emit('evolution:weights_updated', {
      timestamp: Date.now()
    });
  }

  /**
   * Get memory snapshot
   */
  snapshot() {
    return {
      historySize: this.history.length,
      scores: Object.fromEntries(this.scores)
    };
  }
}

const evolutionMemory = new EvolutionMemory();

module.exports = { EvolutionMemory, evolutionMemory };