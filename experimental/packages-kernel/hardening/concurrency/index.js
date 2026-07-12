// PAMASMMA Kernel - Concurrency & Transaction Safety Layer (Milestone 6 Phase 6.2)
// Introduces atomic task execution, mutex locking, and safe parallel job handling

class Mutex {
  constructor() {
    this.locked = false;
    this.queue = [];
  }

  async acquire() {
    const ticket = new Promise(resolve => {
      this.queue.push(resolve);
    });

    if (!this.locked) {
      this.locked = true;
      const next = this.queue.shift();
      if (next) next();
    }

    await ticket;
  }

  release() {
    if (this.queue.length > 0) {
      const next = this.queue.shift();
      next();
    } else {
      this.locked = false;
    }
  }
}

class TaskQueue {
  constructor(concurrency = 2) {
    this.concurrency = concurrency;
    this.running = 0;
    this.queue = [];
  }

  /**
   * Add task to queue
   */
  add(task) {
    return new Promise((resolve, reject) => {
      this.queue.push({ task, resolve, reject });
      this._next();
    });
  }

  /**
   * Execute next task if capacity allows
   */
  async _next() {
    if (this.running >= this.concurrency) return;
    if (this.queue.length === 0) return;

    const { task, resolve, reject } = this.queue.shift();
    this.running++;

    try {
      const result = await this._runAtomic(task);
      resolve(result);
    } catch (err) {
      reject(err);
    } finally {
      this.running--;
      this._next();
    }
  }

  /**
   * Atomic execution wrapper
   */
  async _runAtomic(task) {
    const mutex = task.mutex || new Mutex();

    await mutex.acquire();

    try {
      const result = await task.fn();
      return {
        status: 'completed',
        result
      };
    } catch (err) {
      return {
        status: 'failed',
        error: err.message
      };
    } finally {
      mutex.release();
    }
  }
}

class ConcurrencyEngine {
  constructor() {
    this.queue = new TaskQueue(4);
  }

  /**
   * Submit atomic job
   */
  submit(fn, meta = {}) {
    return this.queue.add({ fn, ...meta });
  }

  /**
   * Batch submit jobs
   */
  async batch(jobs = []) {
    return Promise.all(jobs.map(j => this.submit(j.fn, j.meta)));
  }
}

const concurrencyEngine = new ConcurrencyEngine();

module.exports = { Mutex, TaskQueue, ConcurrencyEngine, concurrencyEngine };