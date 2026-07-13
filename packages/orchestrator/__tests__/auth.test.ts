/**
 * Auth middleware tests.
 *
 * We reload the module after mutating process.env so each test starts
 * with a fresh VALID_KEYS set. jest.resetModules() + require() handles this.
 */

import { Request, Response, NextFunction } from 'express';

function makeReq(
  path: string,
  authorization?: string
): Partial<Request> {
  return {
    path,
    headers: authorization ? { authorization } : {},
  };
}

function makeRes(): { status: jest.Mock; json: jest.Mock; _status?: number } {
  const res: { status: jest.Mock; json: jest.Mock; _status?: number } = {
    status: jest.fn().mockReturnThis(),
    json: jest.fn().mockReturnThis(),
  };
  return res;
}

function loadMiddleware() {
  jest.resetModules();
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  return require('../src/middleware/auth').authMiddleware as (
    req: Request,
    res: Response,
    next: NextFunction
  ) => void;
}

const next: jest.Mock = jest.fn();

beforeEach(() => {
  next.mockClear();
  delete process.env['API_KEYS'];
  delete process.env['NODE_ENV'];
});

describe('authMiddleware — /health bypass', () => {
  it('always passes /health through without auth headers', () => {
    process.env['API_KEYS'] = 'secret1';
    const middleware = loadMiddleware();
    const req = makeReq('/health');
    const res = makeRes();

    middleware(req as Request, res as unknown as Response, next);

    expect(next).toHaveBeenCalledTimes(1);
    expect(res.status).not.toHaveBeenCalled();
  });
});

describe('authMiddleware — no API_KEYS set', () => {
  it('allows all requests in development mode (NODE_ENV=development)', () => {
    process.env['NODE_ENV'] = 'development';
    const middleware = loadMiddleware();
    const req = makeReq('/tasks');
    const res = makeRes();

    middleware(req as Request, res as unknown as Response, next);

    expect(next).toHaveBeenCalledTimes(1);
  });

  it('returns 500 in production when API_KEYS is not configured', () => {
    process.env['NODE_ENV'] = 'production';
    const middleware = loadMiddleware();
    const req = makeReq('/tasks');
    const res = makeRes();

    middleware(req as Request, res as unknown as Response, next);

    expect(res.status).toHaveBeenCalledWith(500);
    expect(next).not.toHaveBeenCalled();
  });
});

describe('authMiddleware — with API_KEYS configured', () => {
  beforeEach(() => {
    process.env['API_KEYS'] = 'valid-key-1, valid-key-2';
  });

  it('allows a request with a valid Bearer token', () => {
    const middleware = loadMiddleware();
    const req = makeReq('/tasks', 'Bearer valid-key-1');
    const res = makeRes();

    middleware(req as Request, res as unknown as Response, next);

    expect(next).toHaveBeenCalledTimes(1);
  });

  it('allows a request with the second valid key', () => {
    const middleware = loadMiddleware();
    const req = makeReq('/tasks', 'Bearer valid-key-2');
    const res = makeRes();

    middleware(req as Request, res as unknown as Response, next);

    expect(next).toHaveBeenCalledTimes(1);
  });

  it('returns 401 when Authorization header is absent', () => {
    const middleware = loadMiddleware();
    const req = makeReq('/tasks');
    const res = makeRes();

    middleware(req as Request, res as unknown as Response, next);

    expect(res.status).toHaveBeenCalledWith(401);
    expect(next).not.toHaveBeenCalled();
  });

  it('returns 401 when header does not use Bearer scheme', () => {
    const middleware = loadMiddleware();
    const req = makeReq('/tasks', 'Basic dXNlcjpwYXNz');
    const res = makeRes();

    middleware(req as Request, res as unknown as Response, next);

    expect(res.status).toHaveBeenCalledWith(401);
  });

  it('returns 403 when Bearer token is not in the key list', () => {
    const middleware = loadMiddleware();
    const req = makeReq('/tasks', 'Bearer wrong-key');
    const res = makeRes();

    middleware(req as Request, res as unknown as Response, next);

    expect(res.status).toHaveBeenCalledWith(403);
    expect(next).not.toHaveBeenCalled();
  });

  it('trims whitespace from keys in API_KEYS', () => {
    // 'valid-key-2' has surrounding spaces in the env var
    const middleware = loadMiddleware();
    const req = makeReq('/tasks', 'Bearer valid-key-2');
    const res = makeRes();

    middleware(req as Request, res as unknown as Response, next);

    expect(next).toHaveBeenCalledTimes(1);
  });
});
