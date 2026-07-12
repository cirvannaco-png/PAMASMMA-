import { ContentGenerator } from '../domain/contentGenerator';
import { MemoryManager } from '@pamasmma/memory-core';

export class ContentAgentAppService {
  constructor(
    private contentGenerator: ContentGenerator,
    private memoryManager: MemoryManager
  ) {}

  async generateContent(
    tenantId: string,
    taskId: string,
    prompt: string
  ): Promise<string> {
    const content = this.contentGenerator.generate(prompt);

    await this.memoryManager.writeMemory(
      {
        type: 'episodic',
        id: taskId,
        data: { content },
        timestamp: new Date().toISOString(),
      },
      { source: 'domain', tenant_id: tenantId, task_id: taskId }
    );

    return content;
  }

  async generateCaption(
    tenantId: string,
    taskId: string,
    topic: string
  ): Promise<{ caption: string; hashtags: string[] }> {
    const result = this.contentGenerator.generateCaption(topic);

    await this.memoryManager.writeMemory(
      {
        type: 'episodic',
        id: `${taskId}-caption`,
        data: { ...result, topic },
        timestamp: new Date().toISOString(),
      },
      { source: 'domain', tenant_id: tenantId, task_id: taskId }
    );

    return result;
  }
}
