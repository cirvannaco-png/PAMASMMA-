// PAMASMMA AI Governance - Reflection Interface (Milestone 5 Phase 5.6)
// Final governance layer: unifies audit + adaptive intelligence into system-wide reflection

const { aiGovernanceAudit } = require('../audit');
const { adaptiveGovernanceEngine } = require('../adaptive');

class GovernanceReflection {
  constructor() {
    this.history = [];
  }

  /**
   * Generate system-wide reflection snapshot
   */
  reflect() {
    const stats = aiGovernanceAudit.getStats();
    const latestAdaptive = adaptiveGovernanceEngine.latest();

    const rejectionRate = stats.total > 0
      ? stats.rejected / stats.total
      : 0;

    const snapshot = {
      timestamp: Date.now(),
      stats,
      rejectionRate,
      adaptive: latestAdaptive || null,
      summary: this._summary(rejectionRate)
    };

    this.history.push(snapshot);

    return snapshot;
  }

  _summary(rejectionRate) {
    return {
      systemState: rejectionRate > 0.3 ? 'unstable' : 'stable',
      insight: 'Unified governance reflection layer active'
    };
  }

  historyLog() {
    return [...this.history];
  }
}

const governanceReflection = new GovernanceReflection();

module.exports = { GovernanceReflection, governanceReflection };