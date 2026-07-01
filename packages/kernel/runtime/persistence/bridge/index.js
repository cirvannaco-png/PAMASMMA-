// PAMASMMA Kernel - Persistence Bridge (Milestone 4 Phase 4.5)
// Connects Execution Runtime → State Engine → Memory Core
// This is the first coherence + persistence wiring layer

const { eventBus } = require('../../../event-bus');

class PersistenceBridge {
  constructor() {
    this.stateEngine = null;
    this.memoryCore = null;
  }

  /**
   * Attach external kernel modules
   */
  bind({ stateEngine, memoryCore }) {
    this.stateEngine = stateEngine;
    this.memoryCore = memoryCore;

    this._wireEvents();
  }

  /**
   * Wire execution lifecycle into persistence layers
   */
  _wireEvents() {
    // Execution success → state + memory
    eventBus.on('execution:complete', (result) => {
      this._commitState(result);
      this._commitMemory(result);
    });

    // Execution error → state + memory
    eventBus.on('execution:error', (error) => {
      this._commitError(error);
    });
  }

  /**
   * State transition commit
   */
  _commitState(result) {
    if (!this.stateEngine) return;

    // Lightweight state snapshot
    this.stateEngine.lastExecution = {
      id: result.taskId,
      status: result.status,
      timestamp: result.executedAt || Date.now()
    };
  }

  /**
   * Memory persistence commit
   */
  _commitMemory(result) {
    if (!this.memoryCore) return;

    if (typeof this.memoryCore.record === 'function') {
      this.memoryCore.record({
        type: 'execution',
        payload: result,
        timestamp: Date.now()
      });
    }
  }

  /**
   * Error persistence path
   */
  _commitError(error) {
    if (this.memoryCore && typeof this.memoryCore.record === 'function') {
      this.memoryCore.record({
        type: 'execution_error',
        payload: error,
        timestamp: Date.now()
      });
    }
  }
}

const persistenceBridge = new PersistenceBridge();

module.exports = { PersistenceBridge, persistenceBridge };