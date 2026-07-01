// PAMASMMA AI Governance Audit Layer (Milestone 5 Phase 5.4)
// Records, analyzes, and traces all AI → Kernel decisions

const { eventBus } = require('../../../kernel/event-bus');

class AIGovernanceAudit {
  constructor() {
    this.logs = [];
    this.rejected = [];
    this.approved = [];

    this._wire();
  }

  /**
   * Bind to system-wide AI events
   */
  _wire() {
    // Track accepted decisions
    eventBus.on('ai:decision', (payload) => {
      this.logs.push({
        type: 'decision',
        payload,
        timestamp: Date.now()
      });

      this.approved.push(payload);
    });

    // Track rejected AI plans
    eventBus.on('ai:rejected', (payload) => {
      this.logs.push({
        type: 'rejected',
        payload,
        timestamp: Date.now()
      });

      this.rejected.push(payload);
    });

    // Track execution results
    eventBus.on('execution:complete', (payload) => {
      this.logs.push({
        type: 'execution_complete',
        payload,
        timestamp: Date.now()
      });
    });

    eventBus.on('execution:error', (payload) => {
      this.logs.push({
        type: 'execution_error',
        payload,
        timestamp: Date.now()
      });
    });
  }

  /**
   * Get full audit trail
   */
  getLogs() {
    return [...this.logs];
  }

  /**
   * Get summary stats
   */
  getStats() {
    return {
      total: this.logs.length,
      approved: this.approved.length,
      rejected: this.rejected.length
    };
  }
}

const aiGovernanceAudit = new AIGovernanceAudit();

module.exports = { AIGovernanceAudit, aiGovernanceAudit };