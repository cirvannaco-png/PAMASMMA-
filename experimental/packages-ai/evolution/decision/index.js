// PAMASMMA AI Evolution Layer - Decision Intelligence & Utility Optimization (Milestone 7 Phase 7.9)
// Final layer: converts uncertainty, causality, and competition into actionable decisions

const { eventBus } = require('../../../kernel/event-bus');
const { evolutionEngine } = require('../core');
const { probabilisticForecastEngine } = require('../probabilistic');
const { temporalCausalModel } = require('../temporal');

/**
 * This is not intelligence.
 * This is the final compression point where competing futures are forced into a single action.
 */
class DecisionEngine {
  constructor() {
    this.history = [];
  }

  /**
   * Expected utility estimation across agents and forecasts
   */
  _utility(agentName, state = {}) {
    const agent = evolutionEngine.agents.get(agentName);
    if (!agent) return -Infinity;

    const belief = probabilisticForecastEngine.beliefs.get(agentName) || {
      confidence: 0.5,
      variance: 0.5
    };

    const weight = agent.weight || 1;
    const confidence = belief.confidence;

    // utility penalized by uncertainty
    return (weight * confidence) - belief.variance;
  }

  /**
   * Evaluate all agents as competing decision hypotheses
   */
  evaluateCandidates(state = {}) {
    const agents = Array.from(evolutionEngine.agents.keys());

    const scored = agents.map(name => ({
      name,
      utility: this._utility(name, state)
    }));

    scored.sort((a, b) => b.utility - a.utility);

    return scored;
  }

  /**
   * Select best action (winner-takes-action compression)
   */
  decide(state = {}) {
    const candidates = this.evaluateCandidates(state);

    if (!candidates.length) return null;

    const best = candidates[0];

    const decision = {
      chosen: best.name,
      utility: best.utility,
      timestamp: Date.now(),
      competitors: candidates.slice(0, 5)
    };

    this.history.push(decision);

    eventBus.emit('evolution:decision:made', decision);

    return decision;
  }

  /**
   * Evaluate regret (post-hoc mismatch between expected and observed outcomes)
   */
  evaluateOutcome(decision, actualUtility) {
    const regret = Math.max(0, decision.utility - actualUtility);

    eventBus.emit('evolution:decision:regret', {
      decision: decision.chosen,
      regret
    });

    return regret;
  }

  /**
   * Snapshot decision state
   */
  snapshot() {
    return {
      decisions: this.history.length,
      last: this.history[this.history.length - 1] || null
    };
  }
}

const decisionEngine = new DecisionEngine();

module.exports = { DecisionEngine, decisionEngine };