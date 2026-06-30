export interface MCPToolDefinition {
  server: string;
  toolName: string;
  riskLevel: 'low' | 'medium' | 'high' | 'critical';
  requiresApproval: boolean;
  maliRequired: boolean;
}

import * as fs from 'fs';
import * as chokidar from 'chokidar';

export class ToolRegistry {
  private tools: Map<string, MCPToolDefinition> = new Map();
  private watcher: chokidar.FSWatcher | null = null;

  loadFromFile(filePath: string) {
    const load = () => {
      try {
        const raw = fs.readFileSync(filePath, 'utf-8');
        const config = JSON.parse(raw);
        this.tools.clear();
        for (const server of config.servers) {
          for (const tool of server.tools) {
            this.tools.set(tool.name, {
              server: server.address,
              toolName: tool.name,
              riskLevel: tool.risk_level,
              requiresApproval: tool.requires_approval,
              maliRequired: tool.mali_required,
            });
          }
        }
        console.log('Tool registry reloaded successfully');
      } catch (err) {
        console.error('Failed to reload tool registry:', err);
      }
    };
    load();
    this.watcher = chokidar.watch(filePath).on('change', load);
  }

  getTool(name: string): MCPToolDefinition | undefined {
    return this.tools.get(name);
  }

  shutdown() {
    this.watcher?.close();
  }
}