// PAMASMMA Kernel - Scheduler + Concurrency Fusion Layer (Milestone 6 Phase 6.3)
// Unifies scheduling engine with concurrency-safe execution pipeline

const { eventBus } = require('../../event-bus');
const { schedulerEngine } = require('../../scheduler');
const { concurrencyEngine } = require('../../hardening/concurrency');

/**
 * SchedulerFusionEngine
 * Bridges scheduled tasks into safe parallel execution lanes
 */
class SchedulerFusionEngine {
  constructor() {
    this.active = false;
  }

  /**
   * Start fusion layer
   */
  start() {
    if (this.active) return;
    this.active = true;

    // Listen to scheduler updates
    schedulerEngine.onUpdate((tasks = []) => {
      this._executeTasks(tasks);
    });

    eventBus.emit('scheduler:fusion:active', {
      timestamp: Date.now()
    });
  }

  /**
   * Execute scheduled tasks via concurrency engine
   */
  async _executeTasks(tasks) {
    if (!Array.isArray(tasks)) return;

    const jobs = tasks.map(task => {
      return {
        fn: async () => {
          // Wrap execution unit
          if (typeof task.handler === 'function') {
            return await task.handler(task.payload);
          }

          if (task.fn) {
            return await task.fn(task.payload);
          }

          return { status: 'no-op', task };
        },
        meta: {
          priority: task.priority || 5
        }
      };
    });

    try {
      const results = await concurrencyEngine.batch(jobs);

      eventBus.emit('scheduler:fusion:complete', {
        results,
        timestamp: Date.now()
      });

      return results;
    } catch (err) {
      eventBus.emit('scheduler:fusion:error', {
        error: err.message,
        timestamp: Date.now()
      });

      throw err;
    }
  }
}

const schedulerFusionEngine = new SchedulerFusionEngine();

module.exports = { SchedulerFusionEngine, schedulerFusionEngine };