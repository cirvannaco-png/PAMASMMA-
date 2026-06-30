import { generateUUID } from '@pamasmma/shared';

export interface Task {
  id: string;
  tenant_id: string;
  type: 'content' | 'marketing' | 'social' | 'email';
  input: Record<string, unknown>;
  created_at: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
}

export class TaskCreator {
  create(data: { tenant_id: string; type: string; input: unknown }): Task {
    return {
      id: generateUUID(),
      tenant_id: data.tenant_id,
      type: data.type as any,
      input: data.input as Record<string, unknown>,
      created_at: new Date().toISOString(),
      status: 'pending',
    };
  }
}

export class TaskRouter {
  route(task: Task): string {
    // Simple routing logic: map task type to agent
    const routes: Record<string, string> = {
      content: 'content-agent',
      marketing: 'marketing-agent',
      social: 'social-agent',
      email: 'email-agent',
    };
    return routes[task.type] || 'default-agent';
  }
}