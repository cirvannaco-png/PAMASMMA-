import { SystemEvent } from './events';
export interface IEventBus {emit(event: SystemEvent): Promise<void>; subscribe(handler: (event: SystemEvent) => void): void;}
export interface IMaliService {evaluate(taskId: string, inputs: unknown): Promise<'approve' | 'revise' | 'reject'>;}
export interface IMCPClient {call(server: string, toolName: string, inputs: unknown): Promise<unknown>;}