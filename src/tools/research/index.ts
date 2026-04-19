import type { OpenClawPluginApi } from 'openclaw/plugin-sdk';
import { registerResearchPublish } from './publish.js';
import { registerResearchPickTopic } from './pick-topic.js';
import { registerResearchSearchWorks } from './search-works.js';

export function registerResearchTools(api: OpenClawPluginApi): void {
  registerResearchPublish(api);
  registerResearchPickTopic(api);
  registerResearchSearchWorks(api);
}
