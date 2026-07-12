// STUB: These modules are placeholders. They return fixed values and do not
// perform real AI inference. Do not treat their outputs as meaningful.
// Each must be replaced with a real model call before this subsystem ships.

export class PerceptionModule {
  // STUB: extracts no real features — returns hardcoded shape
  analyzeInput(input: Record<string, unknown>): Record<string, unknown> {
    return {
      features_extracted: false,
      input_hash: JSON.stringify(input),
    };
  }
}

export class ReasoningModule {
  // STUB: applies no logic — confidence is a constant, not computed
  reason(_perception: Record<string, unknown>): Record<string, unknown> {
    return {
      reasoning_complete: false,
      confidence: 0, // STUB: replace with real inference score
    };
  }
}

export class PredictionModule {
  // STUB: always predicts 'success' regardless of input
  predict(_reasoning: Record<string, unknown>): Record<string, unknown> {
    return {
      predicted_outcome: 'unknown', // STUB: replace with model output
      risk_level: 'unknown',        // STUB: replace with computed risk
    };
  }
}

export class DecisionModule {
  // STUB: always returns 'proceed' — no real decision logic
  decide(_prediction: Record<string, unknown>): Record<string, unknown> {
    return {
      action: 'defer',           // STUB: replace with real decision
      approval_required: true,   // STUB: safe default until real logic exists
    };
  }
}

export class AdaptationModule {
  // STUB: stores no state, applies no adaptation
  adapt(_feedback: Record<string, unknown>): Record<string, unknown> {
    return {
      adapted: false,        // STUB: replace with real adaptation
      new_parameters: {},
    };
  }
}
