import { generateUUID } from '@pamasmma/shared';
export interface Task {id: string; tenant_id: string; type: string; input: unknown; created_at: string;}
export class TaskCreator {create(params: { tenant_id: string; type: string; input: unknown }): Task {return {id: generateUUID(), tenant_id: params.tenant_id, type: params.type, input: params.input, created_at: new Date().toISOString();};}}
export class TaskRouter {route(task: Task): string {switch (task.type) {case 'content': return 'content-agent'; case 'marketing': return 'marketing-intel'; default: return 'content-agent';}}}