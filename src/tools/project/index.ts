import type { OpenClawPluginApi } from 'openclaw/plugin-sdk';
import { registerProjectIngest } from './ingest.js';
import { registerProjectCreate } from './create.js';

export function registerProjectTools(api: OpenClawPluginApi): void {
  registerProjectIngest(api);
  registerProjectCreate(api);
}
