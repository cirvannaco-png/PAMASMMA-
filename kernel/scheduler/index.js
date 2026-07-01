// PAMASMMA Kernel - Scheduler (Deterministic Execution Engine + Enforcement Bridge Integration)
// Now fully integrated with contracts + invariants + state enforcement gate

const { eventBus } = require('../event-bus');
const { registry } = require('../registry');
const { state } = require('../state');
const { enforcementBridge } = require('../enforcement');

class Scheduler {
  constructor() {
    this.running = false;
    this.queue = [];
  }

  initialize() {
    this.running = true;
    this.queue = [];

    eventBus.emit('scheduler:initialized');
  }

  stop() {
    this.running = false;
    eventBus.emit('scheduler:stopped');
  }

  registerStep(name, fn) {
    const wrappedFn = enforcementBridge.wrap(name, fn);

    this.queue.push({ name, fn: wrappedFn });

    eventBus.emit('scheduler:step_registered', { name });
  }

  run(context = {}) {
    if (!this.running) {
      return { status: 'STOPPED' };
    }

    const results = [];

    for (const step of this.queue) {
      try {
        const result = step.fn({
          context,
          registry,
          state: state.getState()
        });

        results.push({ step: step.name, result });
      } catch (err) {
        eventBus.emit('scheduler:error', { step: step.name, error: err.message });

        return {
          status: 'FAILED',
          failedStep: step.name,
          error: err.message
        };
      }
    }

    return {
      status: 'SUCCESS',
      results
    };
  }

  snapshot() {
    return {
      running: this.running,
      steps: this.queue.length
    };
  }
}

const scheduler = new Scheduler();

module.exports = { Scheduler, scheduler };