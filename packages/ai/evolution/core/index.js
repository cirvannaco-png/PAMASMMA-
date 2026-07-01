// PAMASMMA AI Evolution Layer - Core Engine (Milestone 7 Phase 7.1)
// Multi-agent reasoning + policy competition + goal emergence scaffold

const { eventBus } = require('../../../kernel/event-bus');

/**
 * NOTE:
 * This is not intelligence yet. It is a controlled substrate for intelligence emergence.
 * If you expect autonomy here, you are prematurely romanticizing the system.
 */

class EvolutionEngine {
  constructor() {
    this.agents = new Map();
    this.policies = new Map();
    this.goals = [];
    this.tickCount = 0;
    this.active = false;
  }

  /**
   * Register reasoning agent
   */
  registerAgent(name, agentFn, weight = 1) {
    this.agents.set(name, { agentFn, weight });
  }

  /**
   * Register governance / behavior policy
   */
  registerPolicy(name, policyFn, strength = 1) {
    this.policies.set(name, { policyFn, strength });
  }

  /**
   * Internal: run policy arbitration
   */
  _applyPolicies(state) {
    let modified = { ...state };

    for (const [name, p] of this.policies.entries()) {
      try {
        modified = p.policyFn(modified, p.strength) || modified;
      } catch (e) {
        eventBus.emit('evolution:policy_error', { name, error: e.message });
      }
    }

    return modified;
  }

  /**
   * Internal: collect agent proposals
   */
  _collectAgentOutputs(state) {
    const outputs = [];

    for (const [name, a] of this.agents.entries()) {
      try {
        const result = a.agentFn(state);
        outputs.push({ name, result, weight: a.weight });
      } catch (e) {
        eventBus.emit('evolution:agent_error', { name, error: e.message });
      }
    }

    return outputs;
  }

  /**
   * Goal emergence (primitive heuristic layer)
   */
  _generateGoals(outputs) {
    const sorted = outputs
      .sort((a, b) => (b.weight || 1) - (a.weight || 1));

    const top = sorted[0];

    if (!top) return;

    const goal = {
      id: `goal_${Date.now()}_${this.tickCount}`,
      source: top.name,
      value: top.result,
      timestamp: Date.now()
    };

    this.goals.push(goal);
    eventBus.emit('evolution:goal_created', goal);
  }

  /**
   * Run evolution cycle
   */
  step(state = {}) {
    if (!this.active) this.active = true;

    this.tickCount++;

    const policyState = this._applyPolicies(state);
    const outputs = this._collectAgentOutputs(policyState);

    this._generateGoals(outputs);

    eventBus.emit('evolution:tick', {
      tick: this.tickCount,
      goals: this.goals.length
    });

    return {
      tick: this.tickCount,
      outputs,
      goals: this.goals
    };
  }

  /**
   * Current snapshot
   */
  snapshot() {
    return {
      agents: this.agents.size,
      policies: this.policies.size,
      goals: this.goals.length,
      tick: this.tickCount
    };
  }
}

const evolutionEngine = new EvolutionEngine();

module.exports = { EvolutionEngine, evolutionEngine };