// PAMASMMA Kernel - System Integration Layer (Milestone 6 Phase 6.5)
// Unifies AI, Governance, Scheduling, Concurrency, Persistence into a single kernel lifecycle graph

const { eventBus } = require('../event-bus');
const { schedulerEngine } = require('../scheduler');
const { schedulerFusionEngine } = require('../scheduler/fusion');
const { intelligentExecutionController } = require('../scheduler/intelligence');
const { concurrencyEngine } = require('../hardening/concurrency');
const { kernelHardeningRuntime } = require('../hardening/runtime');
const { decisionRouter } = require('../../ai/kernel-fusion/decision-router');
const { aiGovernanceAudit } = require('../../ai/governance/audit');
const { adaptiveGovernanceEngine } = require('../../ai/governance/adaptive');
const { governanceReflection } = require('../../ai/governance/reflection');

/**
 * KernelIntegrationLayer
 * ----------------------------------------
 * This is the top-level orchestrator that binds ALL subsystems
 * into a single coherent execution organism.
 */
class KernelIntegrationLayer {
  constructor() {
    this.active = false;
  }

  /**
   * Boot full integrated kernel system
   */
  start() {
    if (this.active) return;
    this.active = true;

    // 1. Start hardening runtime (persistence + recovery)
    kernelHardeningRuntime.start();

    // 2. Start scheduler fusion (task → execution bridge)
    schedulerFusionEngine.start();

    // 3. Start intelligent execution control
    intelligentExecutionController.start();

    // 4. Wire AI decision flow into scheduler
    eventBus.on('ai:decision', (plan) => {
      decisionRouter.route(plan);
    });

    // 5. Persistence hook: save state after execution cycles
    eventBus.on('scheduler:fusion:complete', (data) => {
      kernelHardeningRuntime.saveState({
        lastExecution: data.timestamp,
        metrics: intelligentExecutionController.stats()
      });
    });

    // 6. Observability hooks
    eventBus.on('ai:rejected', (e) => {
      console.warn('[KERNEL] AI plan rejected', e.errors);
    });

    eventBus.on('scheduler:intelligence:blocked', (e) => {
      console.warn('[KERNEL] Execution blocked:', e.reason);
    });

    // 7. Reflection heartbeat
    setInterval(() => {
      const snapshot = governanceReflection.reflect();
      eventBus.emit('kernel:reflection', snapshot);
    }, 10000);

    // 8. Boot signal
    eventBus.emit('kernel:boot:complete', {
      timestamp: Date.now(),
      status: 'integrated_kernel_active'
    });

    console.log('[PAMASMMA] Integrated Kernel fully operational.');
  }
}

const kernelIntegrationLayer = new KernelIntegrationLayer();

module.exports = { KernelIntegrationLayer, kernelIntegrationLayer };