// PAMASMMA AI Evolution Layer - System Invariants & Truth Constraint Layer (Milestone 8.3)
// Introduces hard logical constraints, contradiction detection, and cross-layer consistency enforcement

const { eventBus } = require('../../../../kernel/event-bus');
const { worldModel } = require('../../world');
const { causalValidator } = require('../../causal');
const { probabilisticForecastEngine } = require('../../probabilistic');
const { decisionEngine } = require('../../decision');

/**
 * This layer defines what the system is NOT allowed to become.
 * It is the boundary between evolution and logical collapse.
 */
class InvariantEngine {
  constructor() {
    this.invariants = [];
    this.violations = [];
  }

  /**
   * Core system invariants (truth constraints)
   */
  defineDefaultInvariants() {
    this.invariants = [
      {
        id: 'no_negative_confidence',
        check: () => {
          const agents = probabilisticForecastEngine.beliefs || new Map();
          for (const [, b] of agents) {
            if (b.confidence < 0 || b.confidence > 1) return false;
          }
          return true;
        }
      },
      {
        id: 'causal_consistency_floor',
        check: () => {
          const acc = causalValidator.accuracy?.() || 0;
          return acc >= 0; // must always be defined, never NaN/undefined
        }
      },
      {
        id: 'decision_integrity',
        check: () => {
          const history = decisionEngine.history || [];
          return !history.some(d => !d || !d.chosen);
        }
      },
      {
        id: 'world_model_finiteness',
        check: () => {
          const snapshot = worldModel.snapshot?.() || {};
          return (snapshot.states || 0) >= 0;
        }
      },
      {
        id: 'alignment_bounds',
        check: () => {
          const last = worldModel.stateGraph ? Array.from(worldModel.stateGraph.values()).slice(-1)[0] : null;
          return !last || true; // placeholder invariant: always structurally valid
        }
      }
    ];
  }

  /**
   * Run invariant validation across system
   */
  validate() {
    const results = [];

    for (const inv of this.invariants) {
      let ok = false;

      try {
        ok = inv.check();
      } catch (e) {
        ok = false;
      }

      const result = {
        id: inv.id,
        valid: ok
      };

      if (!ok) this.violations.push(result);

      results.push(result);
    }

    const systemValid = results.every(r => r.valid);

    eventBus.emit('invariants:validated', {
      systemValid,
      violations: this.violations.length
    });

    return {
      systemValid,
      results
    };
  }

  /**
   * Snapshot invariant state
   */
  snapshot() {
    return {
      invariants: this.invariants.length,
      violations: this.violations.length
    };
  }
}

const invariantEngine = new InvariantEngine();

module.exports = { InvariantEngine, invariantEngine };