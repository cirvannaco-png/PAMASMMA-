// PAMASMMA AI Kernel Fusion - Decision Router (Milestone 5 Phase 5.1)
// Bridges AI Orchestration + Reasoning outputs into Kernel Scheduler/Event system

const { eventBus } = require('../../../kernel/event-bus');
const { schedulerEngine } = require('../../../kernel/scheduler');
const { aiGovernanceFirewall } = require('../../../ai/governance/firewall');

/**
 * Decision Router
 * Converts AI reasoning plans into kernel-executable events and scheduled tasks
 */
class DecisionRouter {
  constructor() {
    this.initialized = true;
  }

  /**
   * Accept structured AI execution plan
   * Expected shape (from Reasoning Engine):
   * {
   *   intent,
   *   steps: [],
   *   priority,
   *   metadata
   * }
   */
  route(aiPlan) {
    if (!aiPlan) throw new Error('Invalid AI plan');

    // 0. Governance validation gate
    const validation = aiGovernanceFirewall.validate(aiPlan);
    if (validation.status !== 'approved') {
      eventBus.emit('ai:rejected', {
        errors: validation.errors || [],
        plan: aiPlan,
        timestamp: Date.now()
      });

      return {
        status: 'rejected',
        errors: validation.errors || []
      };
    }

    const safePlan = validation.plan;

    // 1. Emit AI decision event
    const eventRecord = eventBus.emit('ai:decision', {
      intent: safePlan.intent || 'unknown',
      metadata: safePlan.metadata || {},
      timestamp: Date.now()
    });

    // 2. Convert each step into scheduled tasks
    if (Array.isArray(safePlan.steps)) {
      safePlan.steps.forEach((step, index) => {
        schedulerEngine.ingest({
          event: 'ai:task',
          payload: {
            step,
            index,
            intent: safePlan.intent
          },
          timestamp: Date.now(),
          priority: safePlan.priority || 5
        });
      });
    }

    // 3. Force scheduler tick signal
    eventBus.emit('schedule:update', {});

    return {
      status: 'routed',
      event: eventRecord,
      tasks: safePlan.steps?.length || 0
    };
  }
}

const decisionRouter = new DecisionRouter();

module.exports = { DecisionRouter, decisionRouter };