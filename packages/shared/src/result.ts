export class AppError extends Error {constructor(message: string, public readonly code: string, public readonly statusCode = 500) {super(message);}}
export type Result<T, E = AppError> = Success<T> | Failure<E>;
export class Success<T> {readonly ok = true; constructor(public readonly value: T) {}}
export class Failure<E extends AppError> {readonly ok = false; constructor(public readonly error: E) {}}
export const ok = <T>(value: T): Success<T> => new Success(value);
export const fail = <E extends AppError>(error: E): Failure<E> => new Failure(error);