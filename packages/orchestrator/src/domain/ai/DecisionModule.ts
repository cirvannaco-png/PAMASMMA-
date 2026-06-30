export class DecisionModule {
  decide(prediction: Record<string, unknown>): Record<string, unknown> {
    return {
      action: 'proceed',
      approval_required: false,
    };
  }
}