import { generateUUID } from '@pamasmma/shared';

export interface PromptVersion {
  version: string;
  promptHash: string;
  createdAt: string;
  isStable: boolean;
}

export class AgentVersionManager {
  private versions: Map<string, PromptVersion[]> = new Map();

  saveVersion(agentId: string, promptHash: string): PromptVersion {
    const version: PromptVersion = {
      version: `v${Date.now()}`,
      promptHash,
      createdAt: new Date().toISOString(),
      isStable: false,
    };

    if (!this.versions.has(agentId)) {
      this.versions.set(agentId, []);
    }
    this.versions.get(agentId)!.push(version);
    return version;
  }

  getStableVersion(agentId: string): PromptVersion | undefined {
    const agentVersions = this.versions.get(agentId);
    if (!agentVersions) return undefined;
    return agentVersions.find((v) => v.isStable);
  }

  markAsStable(agentId: string, version: string): void {
    const agentVersions = this.versions.get(agentId);
    if (!agentVersions) return;
    for (const v of agentVersions) {
      if (v.version === version) {
        v.isStable = true;
      } else {
        v.isStable = false;
      }
    }
  }
}
