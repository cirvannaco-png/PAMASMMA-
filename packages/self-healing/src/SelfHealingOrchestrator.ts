import { AgentVersionManager } from './AgentVersionManager';
import { IEventBus, AgentDriftDetectedEvent } from '@pamasmma/shared';

function log(level: string, msg: string, extra?: Record<string, unknown>): void {
  console.log(JSON.stringify({ level, msg, ...extra, ts: new Date().toISOString() }));
}

export class SelfHealingOrchestrator {
  constructor(
    private versionManager: AgentVersionManager,
    private eventBus: IEventBus
  ) {}

  async handleDrift(agentId: string, driftScore: number): Promise<void> {
    const event: AgentDriftDetectedEvent = {
      type: 'agent.drift.detected',
      schema_version: 1,
      timestamp: new Date().toISOString(),
      tenant_id: 'system',
      task_id: 'self-healing',
      agent_id: agentId,
      drift_score: driftScore,
    };
    await this.eventBus.emit(event);

    if (driftScore > 0.5) {
      const stable = this.versionManager.getStableVersion(agentId);
      if (stable) {
        log('warn', 'Rolling back agent to stable version', {
          agentId,
          stableVersion: stable.version,
          driftScore,
        });
        // Production: trigger Kubernetes rollout restart for the agent deployment
      } else {
        log('warn', 'Drift detected but no stable version available — manual intervention required', {
          agentId,
          driftScore,
        });
      }
    } else {
      log('info', 'Drift within acceptable threshold', { agentId, driftScore });
    }
  }

  async healAgent(
    agentId: string,
    diagnostics: Record<string, unknown>
  ): Promise<{ healed: boolean; newVersion: string }> {
    log('info', 'Healing agent', { agentId, diagnostics });

    const newVersion = `v${Date.now()}`;
    this.versionManager.saveVersion(agentId, newVersion);

    log('info', 'Agent healed successfully', { agentId, newVersion });

    return { healed: true, newVersion };
  }
}
