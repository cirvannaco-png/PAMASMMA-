export class AppError extends Error {
  constructor(
    message: string,
    public readonly code: string,
    public readonly statusCode = 500
  ) {
    super(message);
    this.name = 'AppError';
  }
}

/**
 * Result<T, E> is either a successful value or a typed failure.
 * E must extend AppError so that failure payloads always carry a code and
 * statusCode — callers can pattern-match on result.ok without any casting.
 */
export type Result<T, E extends AppError = AppError> = Success<T> | Failure<E>;

export class Success<T> {
  readonly ok = true as const;
  constructor(public readonly value: T) {}
}

export class Failure<E extends AppError> {
  readonly ok = false as const;
  constructor(public readonly error: E) {}
}

export const ok = <T>(value: T): Success<T> => new Success(value);
export const fail = <E extends AppError>(error: E): Failure<E> => new Failure(error);
