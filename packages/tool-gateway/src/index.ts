import { ToolRegistry } from './domain/ToolRegistry';
import { InjectionDetector } from './domain/InjectionDetector';
import { ToolExecutionService } from './application/ToolExecutionService';
import { IMaliService, IMCPClient, IEventBus } from '@pamasmma/shared';
import { gatewayServer } from './presentation/gatewayServer';

// Composition root - inject dependencies
export function createToolGateway(
  maliService: IMaliService,
  mcpClient: IMCPClient,
  eventBus: IEventBus
) {
  const registry = new ToolRegistry();
  registry.loadFromFile(process.env.TOOL_CONFIG_PATH || './tool-config.json');

  const detector = new InjectionDetector();
  const service = new ToolExecutionService(registry, detector, maliService, mcpClient, eventBus);
  const app = gatewayServer(service);

  const PORT = process.env.PORT || 3001;
  const server = app.listen(PORT, () => {
    console.log(`Tool Gateway running on port ${PORT}`);
  });

  return { app, service, registry, server };
}
