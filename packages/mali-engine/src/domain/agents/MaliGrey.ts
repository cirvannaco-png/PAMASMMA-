import { Decision } from '../types';

/** Grey team: assesses legal and compliance liability. */
export class MaliGrey {
  assessLiability(decision: Decision): number {
    if (decision.content.includes('medical')) return 0.6;
    if (decision.content.includes('financial')) return 0.5;
    return 0.1;
  }
}
