// PAMASMMA Kernel - Contracts System (Schema + Invariants Enforcement Layer)
// This layer defines execution contracts for all services in the kernel.

const { eventBus } = require('../kernel/event-bus');

class ContractRegistry {
  constructor() {
    this.contracts = new Map();
  }

  /**
   * Register a contract definition
   */
  register(name, contract) {
    this.contracts.set(name, contract);

    eventBus.emit('contract:registered', { name });

    return true;
  }

  /**
   * Validate input against contract
   */
  validate(name, input) {
    const contract = this.contracts.get(name);

    if (!contract) {
      return {
        valid: false,
        error: 'CONTRACT_NOT_FOUND'
      };
    }

    try {
      const result = contract.validate(input);

      if (!result.valid) {
        eventBus.emit('contract:violation', { name, input });
      }

      return result;

    } catch (err) {
      eventBus.emit('contract:error', { name, error: err.message });

      return {
        valid: false,
        error: 'VALIDATION_EXCEPTION'
      };
    }
  }

  /**
   * Snapshot contract system
   */
  snapshot() {
    return {
      contracts: this.contracts.size
    };
  }
}

const contractRegistry = new ContractRegistry();

module.exports = { ContractRegistry, contractRegistry };