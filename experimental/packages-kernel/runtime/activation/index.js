// PAMASMMA Kernel - Runtime Activation Layer (Milestone 4 Phase 4.4)
// This layer self-wires Event → Scheduler → Execution into an autonomous loop

const { eventBus } = require('../../event-bus');
const { schedulerEngine } = require('../../scheduler');
const { executionRuntime } = require('../execution');

class KernelActivation {
  constructor() {
    this.initialized = false;
  }

  /**
   * Bootstraps full kernel runtime loop
   */
  start() {
    if (this.initialized) return;
    this.initialized = true;

    // Start execution runtime
    executionRuntime.start();

    const originalEmit = eventBus.emit.bind(eventBus);

    // Patch event bus to auto-feed scheduler
    eventBus.emit = (event, payload = {}) => {
      const record = originalEmit(event, payload);

      // Prevent internal recursion storms
      if (event !== 'schedule:update') {
        schedulerEngine.ingest(record);
      }

      // Trigger scheduler tick cycle
      originalEmit('schedule:update', {});

      return record;
    };

    // Initial system tick
    originalEmit('schedule:update', {});
  }
}

const kernelActivation = new KernelActivation();

module.exports = { KernelActivation, kernelActivation };