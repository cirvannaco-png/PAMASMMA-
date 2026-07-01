// PAMASMMA Kernel - Enforcement Bridge (Scheduler ↔ Contracts ↔ State ↔ Invariants)
// This module is the final execution gate before any service runs.

const { eventBus } = require('../event-bus');
const { contractRegistry } = require('../../contracts');
const { invariantEngine } = require('../../services/meta/invariants');
const { state } = require('../state');

class EnforcementBridge {
  constructor() {
    this.mode = 'STRICT';
  }

  /**
   * Validate full execution context before scheduler step runs
   */
  validateExecution(stepName, input = {}) {
    // 1. Contract validation
    const contractResult = contractRegistry.validate(stepName, input);

    if (!contractResult.valid) {
      eventBus.emit('enforcement:contract_block', { stepName, contractResult });

      return {
        allowed: false,
        reason: 'CONTRACT_VIOLATION',
        contractResult
      };
    }

    // 2. Invariant validation
    const invariants = invariantEngine.validate();

    if (!invariants.systemValid) {
      eventBus.emit('enforcement:invariant_block', { stepName, invariants });

      return {
        allowed: false,
        reason: 'INVARIANT_FAILURE',
        invariants
      };
    }

    // 3. State snapshot integrity check
    const currentState = state.getState();

    if (!currentState) {
      eventBus.emit('enforcement:state_block', { stepName });

      return {
        allowed: false,
        reason: 'STATE_UNAVAILABLE'
      };
    }

    return {
      allowed: true
    };
  }

  /**
   * Wrap execution step with enforcement
   */
  wrap(stepName, fn) {
    return (context) => {
      const validation = this.validateExecution(stepName, context);

      if (!validation.allowed) {
        return {
          status: 'BLOCKED',
          stepName,
          validation
        };
      }

      try {
        return fn(context);
      } catch (err) {
        eventBus.emit('enforcement:runtime_error', { stepName, error: err.message });

        return {
          status: 'FAILED',
          stepName,
          error: err.message
        };
      }
    };
  }

  snapshot() {
    return {
      mode: this.mode
    };
  }
}

const enforcementBridge = new EnforcementBridge();

module.exports = { EnforcementBridge, enforcementBridge };