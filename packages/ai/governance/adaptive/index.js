// PAMASMMA AI Governance - Adaptive Engine (Milestone 5 Phase 5.5)
// Analyzes audit signals to propose governance improvements (non-auto-mutating)

const { aiGovernanceAudit } = require('../audit');
const { aiGovernanceFirewall } = require('../firewall');

class AdaptiveGovernanceEngine {
  constructor() {
    this.history = [];
  }

  /**
   * Analyze system behavior patterns
   */
  analyze() {
    const stats = aiGovernanceAudit.getStats();
    const logs = aiGovernanceAudit.getLogs();

    const rejectedRate = stats.total > 0 ? stats.rejected / stats.total : 0;

    const recentRejections = logs
      .filter(l => l.type === 'rejected')
      .slice(-20);

    const pattern = this._detectPatterns(recentRejections);

    const insights = {
      stats,
      rejectedRate,
      pattern,
      recommendations: this._generateRecommendations(rejectedRate, pattern)
    };

    this.history.push(insights);

    return insights;
  }

  /**
   * Detect simple failure patterns
   */
  _detectPatterns(rejections) {
    const eventViolations = {};

    for (const r of rejections) {
      const errors = r.payload?.errors || [];

      for (const e of errors) {
        eventViolations[e] = (eventViolations[e] || 0) + 1;
      }
    }

    return eventViolations;
  }

  /**
   * Generate safe recommendations (NO AUTO-APPLY)
   */
  _generateRecommendations(rejectedRate, pattern) {
    const recs = [];

    if (rejectedRate > 0.3) {
      recs.push('High rejection rate detected: consider relaxing AI plan constraints or improving prompt structure.');
    }

    const topIssue = Object.entries(pattern).sort((a,b)=>b[1]-a[1])[0];

    if (topIssue) {
      recs.push(`Most common violation: ${topIssue[0]} (frequency: ${topIssue[1]})`);
    }

    recs.push('Firewall remains read-only. No automatic mutation is permitted.');

    return recs;
  }

  /**
   * Get last analysis snapshot
   */
  latest() {
    return this.history[this.history.length - 1] || null;
  }
}

const adaptiveGovernanceEngine = new AdaptiveGovernanceEngine();

module.exports = { AdaptiveGovernanceEngine, adaptiveGovernanceEngine };