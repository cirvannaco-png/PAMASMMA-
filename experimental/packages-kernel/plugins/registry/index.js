// PAMASMMA Kernel - Plugin Isolation & Registry System (Milestone 6 Phase 6.6)
// Introduces controlled extensibility layer with sandboxed plugin registration

const vm = require('vm');
const { eventBus } = require('../../event-bus');

/**
 * Plugin contract:
 * {
 *   name,
 *   version,
 *   register(kernelContext)
 * }
 */
class PluginRegistry {
  constructor() {
    this.plugins = new Map();
    this.sandboxContext = this._createSandbox();
  }

  /**
   * Create isolated execution sandbox for plugin evaluation
   */
  _createSandbox() {
    return vm.createContext({
      console: {
        log: (...args) => console.log('[PLUGIN]', ...args),
        error: (...args) => console.error('[PLUGIN]', ...args)
      },
      eventBus,
      setTimeout,
      clearTimeout,
      module: {},
      exports: {}
    });
  }

  /**
   * Register plugin safely
   */
  register(pluginSource) {
    try {
      const script = new vm.Script(pluginSource);
      const result = script.runInContext(this.sandboxContext);

      if (!result || !result.name || !result.register) {
        throw new Error('Invalid plugin contract');
      }

      if (this.plugins.has(result.name)) {
        throw new Error(`Plugin already registered: ${result.name}`);
      }

      this.plugins.set(result.name, result);

      // initialize plugin
      result.register({ eventBus });

      eventBus.emit('plugin:registered', {
        name: result.name,
        version: result.version || '0.0.0',
        timestamp: Date.now()
      });

      return { status: 'registered', name: result.name };
    } catch (err) {
      eventBus.emit('plugin:registration_failed', {
        error: err.message,
        timestamp: Date.now()
      });

      return { status: 'failed', error: err.message };
    }
  }

  /**
   * List plugins
   */
  list() {
    return Array.from(this.plugins.values()).map(p => ({
      name: p.name,
      version: p.version
    }));
  }

  /**
   * Get plugin
   */
  get(name) {
    return this.plugins.get(name) || null;
  }
}

const pluginRegistry = new PluginRegistry();

module.exports = { PluginRegistry, pluginRegistry };