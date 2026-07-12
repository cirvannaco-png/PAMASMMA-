import { injectionAttemptsCounter } from '@pamasmma/shared';

/**
 * Injection patterns covering:
 *  - Template engines (Jinja2, Handlebars, Twig, etc.)
 *  - Server-side template injection
 *  - Shell / command injection
 *  - Script injection
 *  - Prompt injection markers
 */
const INJECTION_PATTERNS: RegExp[] = [
  /\{\{.*?\}\}/gi,             // Handlebars / Jinja2 expression
  /\{%.*?%\}/gi,               // Jinja2 / Twig block tags
  /\{#.*?#\}/gi,               // Jinja2 comment tags
  /<\?php/gi,                  // PHP open tag
  /`[^`]*`/gi,                 // Backtick command execution
  /\$\(.*?\)/gi,               // Shell command substitution
  /;\s*(rm|wget|curl|bash|sh|python|node)\b/gi, // Chained shell commands
  /<script\b[^>]*>/gi,         // Script tag injection
  /javascript:/gi,             // JS protocol
  /on\w+\s*=\s*["']/gi,        // Inline event handlers
  /ignore\s+previous\s+instructions?/gi, // LLM prompt injection
  /you\s+are\s+now\s+(?:acting|pretending|playing)/gi, // Role-override injection
  /system\s*prompt/gi,         // System-prompt extraction attempt
  /--.*?\n/g,                  // SQL comment injection
  /'\s*(or|and)\s*'?\d/gi,     // Basic SQL injection
];

export class InjectionDetector {
  /**
   * Scan a value for injection patterns.
   * Recursively inspects objects and arrays so nested payloads are caught.
   * Returns true if an injection is detected.
   */
  scan(input: unknown): boolean {
    return this.scanValue(input);
  }

  private scanValue(value: unknown, depth = 0): boolean {
    if (depth > 10) return false; // guard against circular references

    if (typeof value === 'string') {
      return this.scanString(value);
    }

    if (Array.isArray(value)) {
      return value.some((item) => this.scanValue(item, depth + 1));
    }

    if (typeof value === 'object' && value !== null) {
      return Object.values(value as Record<string, unknown>).some((v) =>
        this.scanValue(v, depth + 1)
      );
    }

    return false;
  }

  private scanString(input: string): boolean {
    for (const pattern of INJECTION_PATTERNS) {
      // Reset stateful regexes before each test
      pattern.lastIndex = 0;
      if (pattern.test(input)) {
        injectionAttemptsCounter.inc();
        return true;
      }
    }
    return false;
  }
}
