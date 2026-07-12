// PAMASMMA AI Evolution Layer - Meta-Intelligence & Self-Modification (Milestone 8.1)
// Introduces controlled self-modification, reflective governance, and architecture evolution constraints

const { eventBus } = require('../../../kernel/event-bus');
const { worldModel } = require('../world');
const { decisionEngine } = require('../decision');
const { evolutionEngine } = require('../core');

/**
 * WARNING:
 * This layer is the boundary between designed intelligence and self-referential architecture.
 * It does NOT allow uncontrolled self-rewriting. All modifications are mediated by governance constraints.
 */
class MetaIntelligence {
  constructor() {
    this.changeProposals = [];
    this.approvedChanges = [];
    this.reflectionHistory = [];
  }

  /**
   * Reflect on system performance and propose improvements
   */
  reflect() {
    const snapshot = worldModel.snapshot();
    const decisions = decisionEngine.history || [];

    const reflection = {
      timestamp: Date.now(),
      systemLoad: snapshot.states,
      decisionCount: decisions.length,
      observedWeaknesses: this._detectWeaknesses(snapshot, decisions)
    };

    this.reflectionHistory.push(reflection);

    eventBus.emit('meta:intelligence:reflection', reflection);

    return reflection;
  }

  /**
   * Detect structural inefficiencies (heuristic analysis only)
   */
  _detectWeaknesses(snapshot, decisions) {
    const weaknesses = [];

    if (snapshot.states > 1000) {
      weaknesses.push('state_graph_overgrowth');
    }

    if (decisions.length < 5) {
      weaknesses.push('insufficient_decision_density');
    }

    return weaknesses;
  }

  /**
   * Propose controlled architectural modifications
   */
  proposeChange(type, description, impactScore = 0.5) {
    const proposal = {
      id: `meta_${Date.now()}_${Math.random().toString(16).slice(2)}`,
      type,
      description,
      impactScore,
      status: 'pending',
      timestamp: Date.now()
    };

    this.changeProposals.push(proposal);

    eventBus.emit('meta:intelligence:proposal_created', proposal);

    return proposal;
  }

  /**
   * Apply ONLY pre-approved modifications (governed self-modification)
   */
  applyChange(proposalId) {
    const proposal = this.changeProposals.find(p => p.id === proposalId);
    if (!proposal) return null;

    // Governance gate: only high-confidence improvements allowed
    if (proposal.impactScore < 0.7) {
      proposal.status = 'rejected';
      return proposal;
    }

    proposal.status = 'applied';
    this.approvedChanges.push(proposal);

    eventBus.emit('meta:intelligence:change_applied', proposal);

    return proposal;
  }

  /**
   * System snapshot of meta-layer
   */
  snapshot() {
    return {
      reflections: this.reflectionHistory.length,
      proposals: this.changeProposals.length,
      approved: this.approvedChanges.length
    };
  }
}

const metaIntelligence = new MetaIntelligence();

module.exports = { MetaIntelligence, metaIntelligence };