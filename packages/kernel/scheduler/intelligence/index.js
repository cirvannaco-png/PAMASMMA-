// PAMASMMA Kernel - Intelligent Execution Control Layer (Milestone 6 Phase 6.4)
// Introduces AI-aware scheduling control: priorities, quotas, and backpressure management

const { eventBus } = require('../../event-bus');
const { schedulerFusionEngine } = require('../fusion');
const { concurrencyEngine } = require('../../hardening/concurrency');
const { decisionRouter } = require('../../../ai/kernel-fusion/decision-router');

class IntelligentExecutionController {
  constructor() {
    this.active = false;

    // execution constraints
    this.maxQueuePerTick = 25;
    this.backpressureThreshold = 100;

    this.lanes = {
      high: [],
      medium: [],
      low: []
    };

    this.metrics = {
      processed: 0,
      throttled: 0,
      blocked: 0
    };
  }

  /**
   * Start intelligent control layer
   */
  start() {
    if (this.active) return;
    this.active = true;

    eventBus.emit('scheduler:intelligence:active', {
      timestamp: Date.now()
    });

    // hook into fusion layer execution stream
    eventBus.on('schedule:update', (tasks = []) => {
      this._ingest(tasks);
    });
  }

  /**
   * Ingest tasks from scheduler/AI layer
   */
  _ingest(tasks) {
    if (!Array.isArray(tasks)) return;

    // backpressure check
    if (tasks.length > this.backpressureThreshold) {
      this.metrics.blocked += 1;
      eventBus.emit('scheduler:intelligence:blocked', {
        reason: 'backpressure_limit_exceeded',
        size: tasks.length,
        timestamp: Date.now()
      });
      return;
    }

    // distribute into priority lanes
    for (const task of tasks) {
      const priority = task.priority || 5;

      if (priority >= 8) this.lanes.high.push(task);
      else if (priority >= 4) this.lanes.medium.push(task);
      else this.lanes.low.push(task);
    }

    this._execute();
  }

  /**
   * Execute tasks with quota control
   */
  async _execute() {
    const batch = [];

    const take = (lane, limit) => {
      while (lane.length && batch.length < limit) {
        batch.push(lane.shift());
      }
    };

    take(this.lanes.high, this.maxQueuePerTick);
    take(this.lanes.medium, this.maxQueuePerTick);
    take(this.lanes.low, this.maxQueuePerTick);

    if (batch.length === 0) return;

    try {
      // route through fusion execution layer
      await schedulerFusionEngine._executeTasks(batch);

      this.metrics.processed += batch.length;

      eventBus.emit('scheduler:intelligence:cycle_complete', {
        processed: batch.length,
        timestamp: Date.now()
      });

    } catch (err) {
      this.metrics.throttled += 1;

      eventBus.emit('scheduler:intelligence:error', {
        error: err.message,
        timestamp: Date.now()
      });
    }
  }

  /**
   * Get execution metrics
   */
  stats() {
    return {
      ...this.metrics,
      queueDepth: {
        high: this.lanes.high.length,
        medium: this.lanes.medium.length,
        low: this.lanes.low.length
      }
    };
  }
}

const intelligentExecutionController = new IntelligentExecutionController();

module.exports = { IntelligentExecutionController, intelligentExecutionController };