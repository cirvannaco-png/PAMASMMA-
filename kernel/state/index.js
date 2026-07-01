// PAMASMMA Kernel - State System (Immutable Snapshots + Reducers)
// Core principle: state is never mutated directly. All changes are reducer-based and versioned.

const { eventBus } = require('../event-bus');

class KernelState {
  constructor() {
    this.current = this._createEmptyState();
    this.history = [];
    this.version = 0;
  }

  /**
   * Initialize state system
   */
  initialize() {
    this.current = this._createEmptyState();
    this.history = [];
    this.version = 0;

    eventBus.emit('state:initialized');
  }

  /**
   * Base empty state
   */
  _createEmptyState() {
    return {
      world: {},
      decisions: [],
      memory: {},
      metadata: {
        createdAt: Date.now()
      }
    };
  }

  /**
   * Apply reducer to generate new immutable state snapshot
   */
  reduce(reducer, payload = {}) {
    const prevState = this.current;

    const nextState = reducer(prevState, payload);

    this.version += 1;

    const snapshot = {
      version: this.version,
      timestamp: Date.now(),
      state: nextState
    };

    this.history.push(snapshot);
    this.current = nextState;

    eventBus.emit('state:updated', snapshot);

    return snapshot;
  }

  /**
   * Get current state (read-only contract)
   */
  getState() {
    return Object.freeze(this.current);
  }

  /**
   * Snapshot history
   */
  getHistory(limit = 50) {
    return this.history.slice(-limit);
  }

  /**
   * Full snapshot
   */
  snapshot() {
    return {
      version: this.version,
      historySize: this.history.length
    };
  }
}

const state = new KernelState();

module.exports = { KernelState, state };