import { injectionAttemptsCounter } from '@pamasmma/shared';

const INJECTION_PATTERNS = [
  /{{.*?}}/gi,  // Template injection
  /{{.*?\|.*?}}/gi,  // Jinja filters
  /<\?php/gi,  // PHP tags
  /`.*?`/gi,  // Backticks for code execution
];

export class InjectionDetector {
  scan(input: unknown): boolean {
    if (typeof input !== 'string') {
      return false;
    }

    for (const pattern of INJECTION_PATTERNS) {
      if (pattern.test(input)) {
        injectionAttemptsCounter.inc();
        console.warn(`Injection pattern detected: ${pattern}`);
        return true;
      }
    }
    return false;
  }
}
