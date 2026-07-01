// PAMASMMA Kernel - Registry (Service Discovery + Dependency Graph)
// Responsible for tracking services and their execution dependencies

const { eventBus } = require('../event-bus');

class Registry {
  constructor() {
    this.services = new Map();
    this.dependencies = new Map();
  }

  /**
   * Initialize registry
   */
  initialize() {
    this.services.clear();
    this.dependencies.clear();

    eventBus.emit('registry:initialized');
  }

  /**
   * Register a service with optional dependencies
   */
  register(name, service, deps = []) {
    this.services.set(name, service);
    this.dependencies.set(name, deps);

    eventBus.emit('registry:service_registered', { name, deps });

    return true;
  }

  /**
   * Resolve service
   */
  get(name) {
    return this.services.get(name);
  }

  /**
   * Get dependency list
   */
  getDependencies(name) {
    return this.dependencies.get(name) || [];
  }

  /**
   * Snapshot registry state
   */
  snapshot() {
    return {
      services: this.services.size,
      dependencies: this.dependencies.size
    };
  }
}

const registry = new Registry();

module.exports = { Registry, registry };