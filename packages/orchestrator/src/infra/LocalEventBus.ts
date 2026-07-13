import { EventEmitter } from 'events';
import { IEventBus, SystemEvent } from '@pamasmma/shared';

/**
 * In-process event bus backed by Node's EventEmitter.
 *
 * This is the real working implementation — every emit() call synchronously
 * delivers the event to all registered subscribers before resolving.
 * Use this in development and single-process deployments.
 *
 * When you have real Kafka infrastructure, swap this for KafkaProducer by
 * passing it into OrchestratorAppService at the composition root (index.ts).
 * The IEventBus interface is the same; no other code changes.
 */
export class LocalEventBus implements IEventBus {
  private readonly emitter = new EventEmitter();
  private static readonly WILDCARD = 'pamasmma:*';

  constructor() {
    // Increase the default listener cap — one subscription per feature in the
    // orchestrator quickly exhausts the default of 10.
    this.emitter.setMaxListeners(100);
  }

  /**
   * Emit an event to all wildcard subscribers and to type-specific channels.
   * Both calls are synchronous under the hood (EventEmitter.emit is sync),
   * so this resolves only after all handlers have been called.
   */
  async emit(event: SystemEvent): Promise<void> {
    this.emitter.emit(LocalEventBus.WILDCARD, event);
    this.emitter.emit(`pamasmma:${event.type}`, event);
  }

  /**
   * Subscribe to every event type (wildcard channel).
   * Matches the IEventBus interface so callers don't need to know about channels.
   */
  subscribe(handler: (event: SystemEvent) => void): void {
    this.emitter.on(LocalEventBus.WILDCARD, handler);
  }

  /**
   * Subscribe to a specific event type for finer-grained consumers.
   * Example: bus.subscribeToType('mali.risk.assessed', handler)
   */
  subscribeToType(type: string, handler: (event: SystemEvent) => void): void {
    this.emitter.on(`pamasmma:${type}`, handler);
  }

  /** Remove a previously registered wildcard handler. */
  unsubscribe(handler: (event: SystemEvent) => void): void {
    this.emitter.off(LocalEventBus.WILDCARD, handler);
  }

  /** Remove a handler from a specific typed channel. */
  unsubscribeFromType(type: string, handler: (event: SystemEvent) => void): void {
    this.emitter.off(`pamasmma:${type}`, handler);
  }

  /** Total number of active listeners across all channels (useful for diagnostics). */
  get listenerCount(): number {
    return this.emitter.eventNames().reduce(
      (sum, name) => sum + this.emitter.listenerCount(name),
      0
    );
  }
}
