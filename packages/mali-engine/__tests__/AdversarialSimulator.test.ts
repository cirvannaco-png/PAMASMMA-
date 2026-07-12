import { AdversarialSimulator } from '../src/domain/AdversarialSimulator';
import { MaliRed } from '../src/domain/agents/MaliRed';
import { MaliBlue } from '../src/domain/agents/MaliBlue';
import { MaliGrey } from '../src/domain/agents/MaliGrey';
import { MaliService } from '../src/application/MaliService';

const decision = (content: string) => ({ content, metadata: {} });

describe('MaliRed', () => {
  const red = new MaliRed();

  it('returns high misuse score for "100% free"', () => {
    expect(red.simulateUserMisuse(decision('100% free offer'))).toBe(0.9);
  });

  it('returns moderate score for "guaranteed"', () => {
    expect(red.simulateUserMisuse(decision('guaranteed results'))).toBe(0.5);
  });

  it('returns low score for safe content', () => {
    expect(red.simulateUserMisuse(decision('great product'))).toBe(0.1);
  });

  it('returns elevated score for competitor mention', () => {
    expect(red.simulateMarketAttack(decision('beat every competitor'))).toBe(0.7);
  });

  it('returns high platform risk for follow4follow', () => {
    expect(red.simulatePlatformRisk(decision('join follow4follow now'))).toBe(0.8);
  });
});

describe('MaliBlue', () => {
  const blue = new MaliBlue();

  it('flags "click here"', () => {
    expect(blue.detectVulnerabilities(decision('click here to win'))).toBe(0.4);
  });

  it('flags "limited time"', () => {
    expect(blue.detectVulnerabilities(decision('limited time offer'))).toBe(0.3);
  });

  it('returns low score for clean content', () => {
    expect(blue.detectVulnerabilities(decision('healthy lifestyle tips'))).toBe(0.1);
  });
});

describe('MaliGrey', () => {
  const grey = new MaliGrey();

  it('flags medical content', () => {
    expect(grey.assessLiability(decision('medical advice here'))).toBe(0.6);
  });

  it('flags financial content', () => {
    expect(grey.assessLiability(decision('financial investment tips'))).toBe(0.5);
  });

  it('returns low score for neutral content', () => {
    expect(grey.assessLiability(decision('coffee recipes'))).toBe(0.1);
  });
});

describe('AdversarialSimulator', () => {
  const sim = new AdversarialSimulator();

  it('approves safe content', () => {
    expect(sim.assess({ content: 'healthy lifestyle', metadata: {} })).toBe('approve');
  });

  it('rejects clearly harmful content', () => {
    // 100% free (0.9 red) + click here (0.4 blue) + medical (0.6 grey) = high
    expect(
      sim.assess({ content: '100% free medical click here', metadata: {} })
    ).toBe('reject');
  });

  it('handles raw string input', () => {
    const result = sim.assess('perfectly fine content');
    expect(['approve', 'revise', 'reject']).toContain(result);
  });

  it('handles null/undefined gracefully', () => {
    const result = sim.assess(null);
    expect(['approve', 'revise', 'reject']).toContain(result);
  });
});

describe('MaliService', () => {
  const service = new MaliService();

  it('returns a valid verdict for safe input', async () => {
    const verdict = await service.evaluate('task-1', { content: 'nice post', metadata: {} });
    expect(['approve', 'revise', 'reject']).toContain(verdict);
  });

  it('rejects clearly risky input', async () => {
    const verdict = await service.evaluate('task-2', {
      content: '100% free medical click here',
      metadata: {},
    });
    expect(verdict).toBe('reject');
  });
});
