import { Policy, retry, circuitBreaker, timeout, handleAll } from 'cockatiel';

// A generic retry policy for transient errors
export const defaultRetryPolicy = retry(handleAll, { maxAttempts: 3, backoff: { type: 'exponential' } });

// Timeout after 5 seconds
export const defaultTimeoutPolicy = timeout(5000);

// Circuit breaker: after 3 failures in 10s, open for 30s
export const defaultCircuitBreaker = circuitBreaker(handleAll, {
  halfOpenAfter: 30_000,
  breaker: Policy.bulkhead(10, 1000), // simple breaker using bulkhead limits
});