// PAMASMMA AI Evolution Layer - Stabilization & Fitness Governance (Milestone 7 Phase 7.4)
// Introduces global fitness function, anti-collapse controls, diversity preservation, and population governance

const { eventBus } = require('../../../kernel/event-bus');
const { evolutionEngine } = require('../core');
const { evolutionMemory } = require('../memory');
const { adversarialEvolution } = require('../adversarial');

/**
 * This layer is the immune system of evolution.
 * Without it, competition becomes collapse.
 */
class EvolutionStabilization {
  constructor() {
    this.maxPopulation = 50;
    this.minDiversity = 0.25; // heuristic entropy threshold
    this.collapseThreshold = 0.15;
  }

  /**
   * Global fitness function (system-level anchor)
   */
  fitness(agentName, agent) {
    const memoryScore = evolutionMemory.scores.get(agentName) || 1;
    const weight = agent.weight || 1;

    // penalize extreme imbalance
    const instabilityPenalty = Math.abs(weight - memoryScore) * 0.1;

    return (weight * 0.6 + memoryScore * 0.4) - instabilityPenalty;
  }

  /**
   * Estimate diversity (simplified entropy proxy)
   */
  _diversityScore() {
    const agents = Array.from(evolutionEngine.agents.values());
    if (agents.length === 0) return 0;

    const weights = agents.map(a => a.weight || 1);
    const avg = weights.reduce((a, b) => a + b, 0) / weights.length;

    const variance = weights.reduce((acc, w) => acc + Math.pow(w - avg, 2), 0) / weights.length;

    return Math.min(1, variance);
  }

  /**
   * Apply stabilization constraints
   */
  stabilize() {
    const agents = Array.from(evolutionEngine.agents.entries());

    // 1. enforce population cap
    if (agents.length > this.maxPopulation) {
      const sorted = agents
        .map(([name, agent]) => ({ name, agent, score: this.fitness(name, agent) }))
        .sort((a, b) => b.score - a.score);

      const survivors = sorted.slice(0, this.maxPopulation);

      evolutionEngine.agents.clear();

      for (const s of survivors) {
        evolutionEngine.agents.set(s.name, s.agent);
      }

      eventBus.emit('evolution:stabilization:population_trimmed', {
        remaining: survivors.length
      });
    }

    // 2. enforce diversity pressure
    const diversity = this._diversityScore();

    if (diversity < this.minDiversity) {
      eventBus.emit('evolution:stabilization:diversity_low', {
        diversity
      });

      // inject noise agents (controlled mutation pressure)
      for (let i = 0; i < 2; i++) {
        evolutionEngine.registerAgent(
          `noise_agent_${Date.now()}_${i}`,
          () => Math.random(),
          0.5
        );
      }
    }

    // 3. collapse detection
    const avgWeight = agents.reduce((a, [, ag]) => a + (ag.weight || 1), 0) / (agents.length || 1);

    if (avgWeight < this.collapseThreshold) {
      eventBus.emit('evolution:stabilization:collapse_detected', {
        avgWeight
      });

      // soft reset pressure
      for (const [name, agent] of agents) {
        agent.weight = Math.max(0.5, (agent.weight || 1) + 0.3);
      }
    }

    return {
      population: agents.length,
      diversity,
      avgWeight
    };
  }

  /**
   * Snapshot system health
   */
  snapshot() {
    return {
      population: evolutionEngine.agents.size,
      diversity: this._diversityScore()
    };
  }
}

const evolutionStabilization = new EvolutionStabilization();

module.exports = { EvolutionStabilization, evolutionStabilization };