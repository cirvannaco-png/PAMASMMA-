// PAMASMMA Kernel - Event Bus (Deterministic Transport Layer)
// STRICT RULE: No business logic allowed. Only message transport.

const { EventEmitter } = require('events');

class KernelEventBus extends EventEmitter {
  constructor() {
    super();
    this.setMaxListeners(1000);
    this.history = [];
  }

  /**
   * Emit event with audit logging
   */
  emit(event, payload) {
    const record = {
      event,
      payload,
      timestamp: Date.now()
    };

    this.history.push(record);

    return super.emit(event, payload);
  }

  /**
   * Subscribe with optional trace logging
   */
  on(event, listener) {
    return super.on(event, listener);
  }

  /**
   * Snapshot event history (debug only)
   */
  snapshot() {
    return {
      events: this.history.length
    };
  }
}

const eventBus = new KernelEventBus();

module.exports = { KernelEventBus, eventBus };