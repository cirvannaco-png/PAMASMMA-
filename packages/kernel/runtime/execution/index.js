// PAMASMMA Kernel - Execution Runtime Wiring (Milestone 4 Phase 4.3)
// First real actuation layer: connects Scheduler → Execution Runtime

const { schedulerEngine } = require('../scheduler');
const { eventBus } = require('../event-bus');

class ExecutionRuntime {
  constructor() {
    this.running = false;
    this.activeJobs = new Map();
  }

  /**
   * Start execution loop
   */
  start() {
    if (this.running) return;
    this.running = true;

    eventBus.on('schedule:update', () => this._tick());
  }

  /**
   * Execution cycle
   */
  _tick() {
    if (!this.running) return;

    const task = schedulerEngine.next();
    if (!task) return;

    this._execute(task);
  }

  /**
   * Execute scheduled task
   */
  async _execute(task) {
    this.activeJobs.set(task.id, task);

    try {
      task.status = 'running';

      // Placeholder execution logic (real services will attach here later)
      const result = {
        taskId: task.id,
        event: task.event,
        payload: task.payload,
        executedAt: Date.now(),
        status: 'completed'
      };

      task.status = 'completed';
      this.activeJobs.delete(task.id);

      eventBus.emit('execution:complete', result);

    } catch (err) {
      task.status = 'failed';
      this.activeJobs.delete(task.id);

      eventBus.emit('execution:error', {
        taskId: task.id,
        error: err.message
      });
    }
  }

  /**
   * Stop runtime
   */
  stop() {
    this.running = false;
  }

  /**
   * Get active jobs
   */
  getActiveJobs() {
    return Array.from(this.activeJobs.values());
  }
}

const executionRuntime = new ExecutionRuntime();

module.exports = { ExecutionRuntime, executionRuntime };