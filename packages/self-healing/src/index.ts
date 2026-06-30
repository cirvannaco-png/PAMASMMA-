import { SelfHealingOrchestrator } from './SelfHealingOrchestrator';
import { AgentVersionManager } from './AgentVersionManager';
import { IEventBus } from '@pamasmma/shared';

export function createSelfHealing(eventBus: IEventBus) {
  const versionManager = new AgentVersionManager();
  const orchestrator = new SelfHealingOrchestrator(versionManager, eventBus);
  return { orchestrator, versionManager };
}

export { SelfHealingOrchestrator, AgentVersionManager };
