// PAMASMMA AI Evolution Layer - Probabilistic Forecasting & Uncertainty (Milestone 7 Phase 7.8)
// Introduces confidence modeling, probabilistic belief updates, and uncertainty-aware decision scoring

const { eventBus } = require('../../../kernel/event-bus');
const { evolutionMemory } = require('../memory');

/**
 * This layer does not claim truth.
 * It models belief under uncertainty.
 */
class ProbabilisticForecastEngine {
  constructor() {
    this.beliefs = new Map(); // agent -> belief state
    this.forecasts = [];
    this.uncertaintyDecay = 0.98;
  }

  /**
   * Initialize belief distribution for an agent
   */
  initAgent(agentName) {
    if (!this.beliefs.has(agentName)) {
      this.beliefs.set(agentName, {
        confidence: 0.5,
        variance: 0.25,
        prior: 0.5
      });
    }
  }

  /**
   * Update belief using simplified Bayesian-like update
   */
  updateBelief(agentName, evidenceScore) {
    this.initAgent(agentName);

    const b = this.beliefs.get(agentName);

    // treat evidenceScore as likelihood proxy
    const likelihood = Math.max(0, Math.min(1, evidenceScore));

    const posterior = (b.prior * b.confidence + likelihood) / 2;

    b.prior = posterior;
    b.confidence = Math.max(0.05, Math.min(0.95, posterior));

    // variance shrinks when confidence stabilizes
    b.variance = b.variance * this.uncertaintyDecay + Math.abs(likelihood - b.confidence);

    this.beliefs.set(agentName, b);

    eventBus.emit('evolution:probabilistic:belief_updated', {
      agentName,
      belief: b
    });

    return b;
  }

  /**
   * Generate probabilistic forecast for an agent output
   */
  forecast(agentName, state = {}) {
    this.initAgent(agentName);

    const b = this.beliefs.get(agentName);

    const noise = Math.random() * b.variance;

    const prediction = {
      agentName,
      confidence: b.confidence,
      variance: b.variance,
      predictionScore: Math.max(0, Math.min(1, b.confidence + noise - b.variance / 2)),
      state
    };

    this.forecasts.push(prediction);

    eventBus.emit('evolution:probabilistic:forecast_created', prediction);

    return prediction;
  }

  /**
   * Compare forecast vs realized outcome
   */
  evaluate(agentName, realizedScore) {
    this.initAgent(agentName);

    const b = this.beliefs.get(agentName);

    const error = Math.abs(realizedScore - b.confidence);

    const adjusted = b.confidence + (realizedScore - b.confidence) * 0.3;

    b.confidence = Math.max(0.05, Math.min(0.95, adjusted));
    b.variance = Math.max(0.01, b.variance + error * 0.1);

    evolutionMemory.scores.set(
      agentName,
      (evolutionMemory.scores.get(agentName) || 1) * (1 - error * 0.2)
    );

    eventBus.emit('evolution:probabilistic:evaluated', {
      agentName,
      error,
      confidence: b.confidence
    });

    return { error, confidence: b.confidence };
  }

  /**
   * System-wide uncertainty snapshot
   */
  snapshot() {
    const agents = Array.from(this.beliefs.entries());

    const avgConfidence = agents.length
      ? agents.reduce((a, [, b]) => a + b.confidence, 0) / agents.length
      : 0;

    const avgVariance = agents.length
      ? agents.reduce((a, [, b]) => a + b.variance, 0) / agents.length
      : 0;

    return {
      agents: agents.length,
      avgConfidence,
      avgVariance,
      forecasts: this.forecasts.length
    };
  }
}

const probabilisticForecastEngine = new ProbabilisticForecastEngine();

module.exports = { ProbabilisticForecastEngine, probabilisticForecastEngine };