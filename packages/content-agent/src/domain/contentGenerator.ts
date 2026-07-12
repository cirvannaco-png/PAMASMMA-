// STUB: ContentGenerator produces template strings, not real generated content.
// Both methods must be replaced with calls to a real generation model (LLM API,
// fine-tuned model, etc.) before this package can be considered functional.

export interface GeneratedCaption {
  caption: string;
  hashtags: string[];
}

export class ContentGenerator {
  // STUB: returns a fixed template — no model inference occurs
  generate(prompt: string): string {
    // TODO: replace with real LLM call
    return `[STUB] Generated content for: ${prompt}`;
  }

  // STUB: returns a fixed hashtag list regardless of topic
  generateCaption(topic: string): GeneratedCaption {
    // TODO: replace with real caption generation
    return {
      caption: `[STUB] Caption for: ${topic}`,
      hashtags: ['#pamasmma', `#${topic.replace(/\s+/g, '').toLowerCase()}`],
    };
  }
}
