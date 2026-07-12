import { Decision } from '../types';

/** Blue team: detects vulnerabilities in content decisions. */
export class MaliBlue {
  detectVulnerabilities(decision: Decision): number {
    if (decision.content.includes('click here')) return 0.4;
    if (decision.content.includes('limited time')) return 0.3;
    return 0.1;
  }
}
