// PAMASMMA Kernel - Scheduler Engine (Milestone 4 Phase 4.2)
// Transforms events into ordered execution plans

class SchedulerEngine {
  constructor() {
    this.queue = [];
    this.processing = false;
    this.subscribers = new Set();
  }

  /**
   * Accept event from Event Bus
   */
  ingest(eventRecord) {
    const task = this._createTask(eventRecord);
    this.queue.push(task);
    this._sortQueue();
    this._notify();
  }

  /**
   * Create internal execution task
   */
  _createTask(eventRecord) {
    return {
      id: `${eventRecord.event}-${eventRecord.timestamp}`,
      event: eventRecord.event,
      payload: eventRecord.payload,
      timestamp: eventRecord.timestamp,
      priority: this._calculatePriority(eventRecord),
      status: 'pending'
    };
  }

  /**
   * Priority heuristic (extendable)
   */
  _calculatePriority(eventRecord) {
    // Basic heuristic: newer critical events can be prioritized later
    if (eventRecord.event.includes('error')) return 10;
    if (eventRecord.event.includes('system')) return 8;
    return 5;
  }

  /**
   * Sort execution queue
   */
  _sortQueue() {
    this.queue.sort((a, b) => b.priority - a.priority);
  }

  /**
   * Subscribe to scheduling updates
   */
  onUpdate(handler) {
    this.subscribers.add(handler);
  }

  /**
   * Notify subscribers
   */
  _notify() {
    for (const fn of this.subscribers) {
      try {
        fn(this.queue);
      } catch (err) {
        console.error('[SchedulerEngine] subscriber error:', err);
      }
    }
  }

  /**
   * Get next task
   */
  next() {
    return this.queue.shift();
  }

  /**
   * Peek current queue
   */
  getQueue() {
    return [...this.queue];
  }

  /**
   * Clear scheduler
   */
  reset() {
    this.queue = [];
  }
}

// Singleton instance
const schedulerEngine = new SchedulerEngine();

module.exports = { SchedulerEngine, schedulerEngine };