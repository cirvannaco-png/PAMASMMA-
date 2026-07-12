export interface GeneratedCaption {
  caption: string;
  hashtags: string[];
}

export class ContentGenerator {
  generate(prompt: string): string {
    return `Generated content for: ${prompt}`;
  }

  generateCaption(topic: string): GeneratedCaption {
    return {
      caption: `Check out this ${topic}!`,
      hashtags: ['#pamasmma', '#marketing', `#${topic}`],
    };
  }
}
