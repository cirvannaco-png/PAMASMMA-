import { LocalEventBus } from '../src/infra/LocalEventBus';
import { SystemEvent } from '@pamasmma/shared';

function makeEvent(overrides: Partial<SystemEvent> = {}): SystemEvent {
  return {
    type: 'task.created',
    schema_version: 1,
    timestamp: new Date().toISOString(),
    tenant_id: 'tenant-1',
    task_id: 'task-abc',
    task_type: 'content',
    input: {},
    ...overrides,
  } as SystemEvent;
}

describe('LocalEventBus', () => {
  let bus: LocalEventBus;

  beforeEach(() => {
    bus = new LocalEventBus();
  });

  it('delivers an emitted event to a wildcard subscriber', async () => {
    const received: SystemEvent[] = [];
    bus.subscribe((e) => received.push(e));

    const event = makeEvent();
    await bus.emit(event);

    expect(received).toHaveLength(1);
    expect(received[0]).toEqual(event);
  });

  it('delivers an event to multiple independent subscribers', async () => {
    const a: SystemEvent[] = [];
    const b: SystemEvent[] = [];
    bus.subscribe((e) => a.push(e));
    bus.subscribe((e) => b.push(e));

    await bus.emit(makeEvent());

    expect(a).toHaveLength(1);
    expect(b).toHaveLength(1);
  });

  it('delivers an event to a type-specific subscriber', async () => {
    const received: SystemEvent[] = [];
    bus.subscribeToType('task.created', (e) => received.push(e));

    await bus.emit(makeEvent({ type: 'task.created' }));

    expect(received).toHaveLength(1);
  });

  it('does NOT deliver to a type-specific subscriber when type differs', async () => {
    const received: SystemEvent[] = [];
    bus.subscribeToType('mali.risk.assessed', (e) => received.push(e));

    await bus.emit(makeEvent({ type: 'task.created' }));

    expect(received).toHaveLength(0);
  });

  it('removes a wildcard subscriber after unsubscribe', async () => {
    const received: SystemEvent[] = [];
    const handler = (e: SystemEvent) => received.push(e);
    bus.subscribe(handler);
    bus.unsubscribe(handler);

    await bus.emit(makeEvent());

    expect(received).toHaveLength(0);
  });

  it('removes a typed subscriber after unsubscribeFromType', async () => {
    const received: SystemEvent[] = [];
    const handler = (e: SystemEvent) => received.push(e);
    bus.subscribeToType('task.created', handler);
    bus.unsubscribeFromType('task.created', handler);

    await bus.emit(makeEvent());

    expect(received).toHaveLength(0);
  });

  it('delivers multiple sequential events in order', async () => {
    const received: string[] = [];
    bus.subscribe((e) => received.push(e.task_id));

    await bus.emit(makeEvent({ task_id: 'first' }));
    await bus.emit(makeEvent({ task_id: 'second' }));
    await bus.emit(makeEvent({ task_id: 'third' }));

    expect(received).toEqual(['first', 'second', 'third']);
  });

  it('reports listenerCount correctly', async () => {
    expect(bus.listenerCount).toBe(0);
    const h = () => {};
    bus.subscribe(h);
    bus.subscribeToType('task.created', h);
    expect(bus.listenerCount).toBe(2);
    bus.unsubscribe(h);
    expect(bus.listenerCount).toBe(1);
  });

  it('is tenant-agnostic — broadcasts to all subscribers regardless of tenant', async () => {
    const received: string[] = [];
    bus.subscribe((e) => received.push(e.tenant_id));

    await bus.emit(makeEvent({ tenant_id: 'alpha' }));
    await bus.emit(makeEvent({ tenant_id: 'beta' }));

    expect(received).toEqual(['alpha', 'beta']);
  });
});
