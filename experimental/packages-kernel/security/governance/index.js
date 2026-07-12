// PAMASMMA Kernel - Security & Permission Governance Layer (Milestone 6 Phase 6.7)
// Defines capability-based security model for AI, plugins, scheduler, and kernel operations

const { eventBus } = require('../../event-bus');

/**
 * Capability-based permissions model:
 * - AI: restricted planning capabilities
 * - PLUGIN: sandboxed event access
 * - SCHEDULER: task creation limits
 * - KERNEL: privileged operations
 */
class SecurityGovernance {
  constructor() {
    this.roles = {
      AI: new Set(['plan:read', 'plan:route']),
      PLUGIN: new Set(['event:emit', 'event:listen']),
      SCHEDULER: new Set(['task:create', 'task:view']),
      KERNEL: new Set(['*'])
    };

    this.revoked = new Map();
  }

  /**
   * Check permission for entity
   */
  can(role, capability) {
    const permissions = this.roles[role];
    if (!permissions) return false;
    if (permissions.has('*')) return true;

    const revoked = this.revoked.get(role) || new Set();
    if (revoked.has(capability)) return false;

    return permissions.has(capability);
  }

  /**
   * Enforce access control
   */
  assert(role, capability, context = {}) {
    const allowed = this.can(role, capability);

    if (!allowed) {
      eventBus.emit('security:violation', {
        role,
        capability,
        context,
        timestamp: Date.now()
      });

      throw new Error(`SECURITY VIOLATION: ${role} cannot perform ${capability}`);
    }

    return true;
  }

  /**
   * Revoke capability dynamically
   */
  revoke(role, capability) {
    if (!this.revoked.has(role)) {
      this.revoked.set(role, new Set());
    }

    this.revoked.get(role).add(capability);

    eventBus.emit('security:revoked', {
      role,
      capability,
      timestamp: Date.now()
    });
  }

  /**
   * Restore capability
   */
  restore(role, capability) {
    const set = this.revoked.get(role);
    if (set) set.delete(capability);

    eventBus.emit('security:restored', {
      role,
      capability,
      timestamp: Date.now()
    });
  }

  /**
   * Get security snapshot
   */
  snapshot() {
    return {
      roles: Object.fromEntries(
        Object.entries(this.roles).map(([k, v]) => [k, Array.from(v)])
      ),
      revoked: Object.fromEntries(
        Array.from(this.revoked.entries()).map(([k, v]) => [k, Array.from(v)])
      )
    };
  }
}

const securityGovernance = new SecurityGovernance();

module.exports = { SecurityGovernance, securityGovernance };