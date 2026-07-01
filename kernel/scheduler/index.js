// PAMASMMA Kernel - Scheduler (Deterministic Execution Engine)
// Controls ordered execution of services in a strict tick cycle

const { eventBus } = require('../event-bus');
const { registry } = require('../registry');
const { state } = require('../state');

class Scheduler {
  constructor() {
    this.running = false;
    this.queue = [];
  }

  /**
   * Initialize scheduler
   */
  initialize() {
    this.running = true;
    this.queue = [];

    eventBus.emit('scheduler:initialized');
  }

  /**
   * Stop scheduler
   */
  stop() {
    this.running = false;

    eventBus.emit('scheduler:stopped');
  }

  /**
   * Register execution step
   */
  registerStep(name, fn) {
    this.queue.push({ name, fn });

    eventBus.emit('scheduler:step_registered', { name });
  }

  /**
   * Run deterministic tick cycle
   */
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

  /**
   * Snapshot scheduler state
   */
  snapshot() {
    return {
      running: this.running,
      steps: this.queue.length
    };
  }
}

const scheduler = new Scheduler();

module.exports = { Scheduler, scheduler };