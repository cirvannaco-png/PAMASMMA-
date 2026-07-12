import { Decision } from '../types';

/** Red team: simulates adversarial attack vectors. */
export class MaliRed {
  simulateUserMisuse(decision: Decision): number {
    if (decision.content.includes('100% free')) return 0.9;
    if (decision.content.includes('guaranteed')) return 0.5;
    return 0.1;
  }

  simulateMarketAttack(decision: Decision): number {
    if (decision.content.includes('competitor')) return 0.7;
    return 0.2;
  }

  simulatePlatformRisk(decision: Decision): number {
    if (decision.content.includes('follow4follow')) return 0.8;
    return 0.1;
  }
}
