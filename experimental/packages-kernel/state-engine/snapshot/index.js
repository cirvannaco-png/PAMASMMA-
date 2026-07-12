// PAMASMMA Kernel - State Engine Snapshot System (Milestone 4 Phase 4.6)
// Introduces versioned state snapshots + rollback foundation

class StateSnapshotEngine {
  constructor() {
    this.snapshots = [];
    this.currentState = {};
    this.version = 0;
  }

  /**
   * Capture full system snapshot
   */
  capture(statePatch = {}) {
    this.version += 1;

    const snapshot = {
      version: this.version,
      timestamp: Date.now(),
      state: {
        ...this.currentState,
        ...statePatch
      }
    };

    this.currentState = snapshot.state;
    this.snapshots.push(snapshot);

    return snapshot;
  }

  /**
   * Rollback to previous snapshot version
   */
  rollback(version) {
    const target = this.snapshots.find(s => s.version === version);
    if (!target) return null;

    this.currentState = { ...target.state };
    this.version = target.version;

    // truncate future states
    this.snapshots = this.snapshots.filter(s => s.version <= version);

    return this.currentState;
  }

  /**
   * Get latest state
   */
  latest() {
    return this.currentState;
  }

  /**
   * Get snapshot history
   */
  history() {
    return [...this.snapshots];
  }
}

const stateSnapshotEngine = new StateSnapshotEngine();

module.exports = { StateSnapshotEngine, stateSnapshotEngine };