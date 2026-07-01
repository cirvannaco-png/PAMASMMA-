// PAMASMMA AI Evolution Layer - Adversarial Dynamics (Milestone 7 Phase 7.3)
// Introduces competition, tournament selection, reward/penalty pressure, and survival dynamics

const { eventBus } = require('../../../kernel/event-bus');
const { evolutionEngine } = require('../core');
const { evolutionMemory } = require('../memory');

/**
 * This layer does not create intelligence.
 * It creates pressure. Intelligence is what survives pressure.
 */
class AdversarialEvolution {
  constructor() {
    this.populationSize = 0;
    this.eliminationRate = 0.2;
  }

  /**
   * Run competition cycle between agents
   */
  runCycle(state = {}) {
    const agents = Array.from(evolutionEngine.agents.entries());
    if (agents.length < 2) return null;

    // score agents based on memory + raw weight
    const scored = agents.map(([name, agent]) => {
      const memoryScore = evolutionMemory.scores.get(name) || 1;
      const score = (agent.weight || 1) * memoryScore;

      return { name, agent, score };
    });

    // sort descending
    scored.sort((a, b) => b.score - a.score);

    const survivorsCount = Math.max(1, Math.floor(scored.length * (1 - this.eliminationRate)));
    const survivors = scored.slice(0, survivorsCount);
    const eliminated = scored.slice(survivorsCount);

    // reward survivors
    for (const s of survivors) {
      s.agent.weight = Math.min(5, (s.agent.weight || 1) + 0.1);
    }

    // penalize eliminated
    for (const e of eliminated) {
      e.agent.weight = Math.max(0.1, (e.agent.weight || 1) - 0.2);
    }

    // optional: weak replacement drift (soft regeneration)
    for (const e of eliminated) {
      const parent = survivors[Math.floor(Math.random() * survivors.length)];
      if (parent) {
        evolutionEngine.registerAgent(
          `${e.name}_mutated_${Date.now()}`,
          parent.agent.agentFn,
          Math.max(0.5, parent.agent.weight * 0.8)
        );
      }
    }

    const report = {
      total: agents.length,
      survivors: survivors.map(s => s.name),
      eliminated: eliminated.map(e => e.name),
      timestamp: Date.now()
    };

    eventBus.emit('evolution:adversarial_cycle', report);

    return report;
  }

  /**
   * Snapshot of population pressure state
   */
  snapshot() {
    return {
      population: evolutionEngine.agents.size,
      eliminationRate: this.eliminationRate
    };
  }
}

const adversarialEvolution = new AdversarialEvolution();

module.exports = { AdversarialEvolution, adversarialEvolution };