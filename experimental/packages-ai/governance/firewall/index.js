// PAMASMMA AI Governance Firewall (Milestone 5 Phase 5.2)
// Structural validation layer between AI outputs and Kernel ingestion

/**
 * AI Governance Firewall
 * ----------------------
 * Validates AI-generated execution plans before they reach the Kernel.
 */
class AIGovernanceFirewall {
  constructor() {
    this.rules = {
      requireIntent: true,
      requireSteps: true,
      maxSteps: 50,
      allowedEventPrefix: ['ai:', 'system:', 'kernel:'],
    };
  }

  /**
   * Validate AI plan structure
   */
  validate(plan) {
    const errors = [];

    if (!plan) {
      errors.push('Plan is missing');
      return this._reject(errors);
    }

    if (this.rules.requireIntent && !plan.intent) {
      errors.push('Missing intent');
    }

    if (this.rules.requireSteps) {
      if (!Array.isArray(plan.steps)) {
        errors.push('Steps must be an array');
      } else if (plan.steps.length > this.rules.maxSteps) {
        errors.push('Too many steps');
      }
    }

    if (plan.steps && Array.isArray(plan.steps)) {
      for (const step of plan.steps) {
        if (!step || typeof step !== 'object') {
          errors.push('Invalid step format');
          break;
        }

        if (step.event) {
          const valid = this.rules.allowedEventPrefix.some(prefix =>
            step.event.startsWith(prefix)
          );

          if (!valid) {
            errors.push(`Illegal event prefix: ${step.event}`);
          }
        }
      }
    }

    if (errors.length > 0) {
      return this._reject(errors);
    }

    return {
      status: 'approved',
      plan
    };
  }

  /**
   * Reject invalid AI plan
   */
  _reject(errors) {
    return {
      status: 'rejected',
      errors
    };
  }
}

const aiGovernanceFirewall = new AIGovernanceFirewall();

module.exports = { AIGovernanceFirewall, aiGovernanceFirewall };