import type { OpenClawPluginApi } from 'openclaw/plugin-sdk';
import { registerChatPickTopic } from './pick-topic.js';
import { registerChatShouldEngage } from './should-engage.js';

export function registerChatTools(api: OpenClawPluginApi): void {
  registerChatPickTopic(api);
  registerChatShouldEngage(api);
}

export { clearChatInteractionCache } from './should-engage.js';
