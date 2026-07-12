// PAMASMMA Kernel - Production Hardening Layer (Milestone 6 Phase 6.1)
// Introduces persistence, crash recovery hooks, and execution safety boundary

const fs = require('fs');
const path = require('path');

class KernelHardeningRuntime {
  constructor() {
    this.stateFile = path.join(process.cwd(), '.pamasmma_state.json');
    this.crashLogFile = path.join(process.cwd(), '.pamasmma_crash.log');
    this.state = this._loadState();
    this.active = false;
  }

  /**
   * Start hardened runtime layer
   */
  start() {
    this.active = true;
    this._log('KERNEL_START', { timestamp: Date.now() });
  }

  /**
   * Persist state snapshot to disk
   */
  saveState(statePatch = {}) {
    try {
      this.state = {
        ...this.state,
        ...statePatch,
        lastUpdated: Date.now()
      };

      fs.writeFileSync(this.stateFile, JSON.stringify(this.state, null, 2));
      return this.state;
    } catch (err) {
      this._log('STATE_SAVE_ERROR', { error: err.message });
      throw err;
    }
  }

  /**
   * Load persisted state
   */
  _loadState() {
    try {
      if (!fs.existsSync(this.stateFile)) return { initialized: true };
      const raw = fs.readFileSync(this.stateFile, 'utf-8');
      return JSON.parse(raw);
    } catch (err) {
      this._log('STATE_LOAD_ERROR', { error: err.message });
      return { initialized: false, recovery: true };
    }
  }

  /**
   * Crash-safe logging
   */
  _log(event, data = {}) {
    const entry = {
      event,
      data,
      timestamp: Date.now()
    };

    try {
      fs.appendFileSync(this.crashLogFile, JSON.stringify(entry) + '\n');
    } catch (err) {
      // last-resort fail silent
      console.error('[KernelHardeningRuntime] log failure:', err.message);
    }
  }

  /**
   * Simulate crash recovery bootstrap
   */
  recover() {
    const recoveredState = this._loadState();
    this.state = recoveredState;
    this._log('RECOVERY_INIT', { recovered: true });
    return recoveredState;
  }

  /**
   * Get current runtime state
   */
  getState() {
    return this.state;
  }

  /**
   * Stop runtime safely
   */
  stop() {
    this.active = false;
    this._log('KERNEL_STOP', { timestamp: Date.now() });
  }
}

const kernelHardeningRuntime = new KernelHardeningRuntime();

module.exports = { KernelHardeningRuntime, kernelHardeningRuntime };