import {
  retry,
  circuitBreaker,
  timeout,
  handleAll,
  ExponentialBackoff,
  ConsecutiveBreaker,
  TimeoutStrategy,
} from 'cockatiel';

/**
 * Retry up to 3 times with exponential backoff on any error.
 * Backoff starts at ~128 ms and doubles each attempt (cockatiel default).
 */
export const defaultRetryPolicy = retry(handleAll, {
  maxAttempts: 3,
  backoff: new ExponentialBackoff(),
});

/**
 * Cancel the wrapped call after 5 seconds.
 * Cooperative strategy: the promise resolves to an AbortError; the caller
 * is responsible for honouring the signal if it needs hard cancellation.
 */
export const defaultTimeoutPolicy = timeout(5_000, TimeoutStrategy.Cooperative);

/**
 * Open the circuit after 3 consecutive failures; attempt recovery after 30 s.
 */
export const defaultCircuitBreaker = circuitBreaker(handleAll, {
  halfOpenAfter: 30_000,
  breaker: new ConsecutiveBreaker(3),
});
