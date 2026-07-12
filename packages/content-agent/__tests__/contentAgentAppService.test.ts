import { ContentAgentAppService } from '../src/application/contentAgentAppService';
import { ContentGenerator } from '../src/domain/contentGenerator';
import { MemoryManager } from '@pamasmma/memory-core';

describe('ContentGenerator', () => {
  let generator: ContentGenerator;

  beforeEach(() => {
    generator = new ContentGenerator();
  });

  it('generates content for a prompt', () => {
    const result = generator.generate('Hello world');
    expect(result).toContain('Hello world');
  });

  it('generates a caption with hashtags', () => {
    const result = generator.generateCaption('fitness');
    expect(result.caption).toContain('fitness');
    expect(result.hashtags).toContain('#fitness');
    expect(result.hashtags.length).toBeGreaterThan(0);
  });

  it('includes #pamasmma in hashtags', () => {
    const result = generator.generateCaption('travel');
    expect(result.hashtags).toContain('#pamasmma');
  });
});

describe('ContentAgentAppService', () => {
  let service: ContentAgentAppService;
  let memory: MemoryManager;

  beforeEach(() => {
    memory = new MemoryManager();
    service = new ContentAgentAppService(new ContentGenerator(), memory);
  });

  it('generates content and persists to memory', async () => {
    const result = await service.generateContent('t1', 'task-1', 'test prompt');
    expect(typeof result).toBe('string');
    expect(result).toContain('test prompt');

    const layer = memory.createAccessLayer('t1');
    const record = layer.getFromSTM('task-1');
    expect(record).toBeDefined();
    expect((record?.data as Record<string, unknown>)['content']).toBe(result);
  });

  it('generates caption and persists to memory', async () => {
    const result = await service.generateCaption('t1', 'task-2', 'cycling');
    expect(result.caption).toContain('cycling');
    expect(result.hashtags).toContain('#cycling');

    const layer = memory.createAccessLayer('t1');
    const record = layer.getFromSTM('task-2-caption');
    expect(record).toBeDefined();
  });
});
