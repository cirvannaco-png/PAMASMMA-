import { Request, Response, NextFunction } from 'express';

const NODE_ENV = process.env['NODE_ENV'] ?? 'development';
const IS_PRODUCTION = NODE_ENV === 'production';

/**
 * Parse API_KEYS from env at startup.
 * Format: comma-separated tokens, e.g.  API_KEYS=key1,key2,key3
 * Whitespace around commas is stripped; empty segments are ignored.
 */
const VALID_KEYS: Set<string> = new Set(
  (process.env['API_KEYS'] ?? '')
    .split(',')
    .map((k) => k.trim())
    .filter((k) => k.length > 0)
);

if (VALID_KEYS.size === 0 && !IS_PRODUCTION) {
  console.warn(
    '[auth] WARNING: API_KEYS env var is not set. ' +
    'All requests are allowed in development mode. ' +
    'Set API_KEYS=<comma-separated tokens> before going to production.'
  );
}

/**
 * Bearer-token auth middleware.
 *
 * Rules:
 *  - /health is always open (monitoring, Kubernetes liveness probes).
 *  - In production with no keys configured: 500 (server misconfiguration).
 *  - In development with no keys configured: pass-through (dev convenience).
 *  - Otherwise: require  Authorization: Bearer <token>  matching a key in API_KEYS.
 */
export function authMiddleware(req: Request, res: Response, next: NextFunction): void {
  // Health check never requires auth
  if (req.path === '/health') {
    next();
    return;
  }

  // No keys configured
  if (VALID_KEYS.size === 0) {
    if (IS_PRODUCTION) {
      res.status(500).json({
        error: 'Server misconfiguration: API_KEYS must be set in production',
      });
      return;
    }
    // Dev-only convenience: allow all
    next();
    return;
  }

  const authHeader = req.headers['authorization'];
  if (!authHeader || !authHeader.startsWith('Bearer ')) {
    res.status(401).json({
      error: 'Unauthorized',
      hint: 'Provide an Authorization: Bearer <token> header',
    });
    return;
  }

  const token = authHeader.slice(7).trim();
  if (!VALID_KEYS.has(token)) {
    res.status(403).json({ error: 'Forbidden: invalid API key' });
    return;
  }

  next();
}
