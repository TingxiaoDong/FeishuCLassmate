import type { OpenClawPluginApi } from 'openclaw/plugin-sdk';
import { registerClassmateCommand } from './classmate.js';

export function registerAllCommands(api: OpenClawPluginApi): void {
  registerClassmateCommand(api);
  // Additional slash commands (tour, supervise, project, equipment) are
  // intentionally not registered as CLI verbs — they're triggered via
  // natural-language in Feishu and fulfilled through the registered tools
  // + skill docs.
}
