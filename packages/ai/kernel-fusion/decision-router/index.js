// PAMASMMA AI Kernel Fusion - Decision Router (Milestone 5 Phase 5.1)
// Bridges AI Orchestration + Reasoning outputs into Kernel Scheduler/Event system

const { eventBus } = require('../../../kernel/event-bus');
const { schedulerEngine } = require('../../../kernel/scheduler');

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

    // 1. Emit AI decision event
    const eventRecord = eventBus.emit('ai:decision', {
      intent: aiPlan.intent || 'unknown',
      metadata: aiPlan.metadata || {},
      timestamp: Date.now()
    });

    // 2. Convert each step into scheduled tasks
    if (Array.isArray(aiPlan.steps)) {
      aiPlan.steps.forEach((step, index) => {
        schedulerEngine.ingest({
          event: 'ai:task',
          payload: {
            step,
            index,
            intent: aiPlan.intent
          },
          timestamp: Date.now(),
          priority: aiPlan.priority || 5
        });
      });
    }

    // 3. Force scheduler tick signal
    eventBus.emit('schedule:update', {});

    return {
      status: 'routed',
      event: eventRecord,
      tasks: aiPlan.steps?.length || 0
    };
  }
}

const decisionRouter = new DecisionRouter();

module.exports = { DecisionRouter, decisionRouter };