import { MaliRed } from './agents/MaliRed';
import { MaliBlue } from './agents/MaliBlue';
import { MaliGrey } from './agents/MaliGrey';
import { Decision } from './types';

export class AdversarialSimulator {
  private red = new MaliRed();
  private blue = new MaliBlue();
  private grey = new MaliGrey();

  assess(decision: unknown): 'approve' | 'revise' | 'reject' {
    const d = this.normaliseDecision(decision);

    const redScore =
      this.red.simulateUserMisuse(d) +
      this.red.simulateMarketAttack(d) +
      this.red.simulatePlatformRisk(d);

    const blueScore = this.blue.detectVulnerabilities(d);
    const greyScore = this.grey.assessLiability(d);

    const totalScore = (redScore + blueScore + greyScore) / 3;

    if (totalScore > 0.7) return 'reject';
    if (totalScore > 0.4) return 'revise';
    return 'approve';
  }

  /** Normalise arbitrary input into a Decision shape for analysis. */
  private normaliseDecision(input: unknown): Decision {
    if (typeof input === 'object' && input !== null) {
      const raw = input as Record<string, unknown>;
      return { content: String(raw['content'] ?? ''), metadata: raw };
    }
    return { content: String(input ?? ''), metadata: {} };
  }
}
