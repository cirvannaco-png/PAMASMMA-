// PAMASMMA Kernel - Event Bus (Milestone 4 Phase 4.1)
// This is the first executable backbone of the kernel runtime

class EventBus {
  constructor() {
    this.handlers = new Map();
    this.history = [];
  }

  /**
   * Register event listener
   */
  on(event, handler) {
    if (!this.handlers.has(event)) {
      this.handlers.set(event, new Set());
    }
    this.handlers.get(event).add(handler);
  }

  /**
   * Remove event listener
   */
  off(event, handler) {
    if (!this.handlers.has(event)) return;
    this.handlers.get(event).delete(handler);
  }

  /**
   * Emit event through system
   */
  emit(event, payload = {}) {
    const eventRecord = {
      event,
      payload,
      timestamp: Date.now()
    };

    this.history.push(eventRecord);

    const handlers = this.handlers.get(event);
    if (!handlers) return eventRecord;

    for (const handler of handlers) {
      try {
        handler(payload, eventRecord);
      } catch (err) {
        console.error(`[EventBus] Handler error for ${event}:`, err);
      }
    }

    return eventRecord;
  }

  /**
   * Get event history
   */
  getHistory() {
    return [...this.history];
  }

  /**
   * Clear all handlers (dangerous, used for reset/recovery)
   */
  reset() {
    this.handlers.clear();
  }
}

// Singleton kernel event bus instance
const eventBus = new EventBus();

module.exports = { EventBus, eventBus };