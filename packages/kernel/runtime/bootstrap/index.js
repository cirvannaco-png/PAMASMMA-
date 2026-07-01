// PAMASMMA Kernel - Bootstrap Orchestrator (Milestone 4 Phase 4.7)
// Single entrypoint that wires the entire Kernel into a bootable system

const { eventBus } = require('../../event-bus');
const { schedulerEngine } = require('../../scheduler');
const { executionRuntime } = require('../execution');
const { kernelActivation } = require('../activation');
const { stateSnapshotEngine } = require('../../state-engine/snapshot');
const { persistenceBridge } = require('../persistence/bridge');

/**
 * Kernel Bootstrap Orchestrator
 * --------------------------------
 * This is the single entrypoint that activates PAMASMMA Kernel runtime.
 * It wires all subsystems into a unified execution organism.
 */
class KernelBootstrap {
  constructor() {
    this.started = false;
  }

  /**
   * Initialize full kernel system
   */
  start() {
    if (this.started) return;
    this.started = true;

    // 1. Bind persistence layer
    persistenceBridge.bind({
      stateEngine: stateSnapshotEngine,
      memoryCore: {
        record: (entry) => {
          // Minimal in-memory fallback memory core (Phase 4 placeholder)
          if (!global.__PAMASMMA_MEMORY__) global.__PAMASMMA_MEMORY__ = [];
          global.__PAMASMMA_MEMORY__.push(entry);
        }
      }
    });

    // 2. Wire scheduler → execution trigger
    schedulerEngine.onUpdate(() => {
      eventBus.emit('schedule:update', {});
    });

    // 3. Activate execution runtime
    executionRuntime.start();

    // 4. Activate kernel autonomous loop
    kernelActivation.start();

    // 5. Seed initial system heartbeat
    eventBus.emit('system:boot', {
      timestamp: Date.now(),
      status: 'kernel_initialized'
    });

    console.log('[PAMASMMA] Kernel fully booted and operational.');
  }
}

const kernelBootstrap = new KernelBootstrap();

module.exports = { KernelBootstrap, kernelBootstrap };