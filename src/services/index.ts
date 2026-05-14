import type { OpenClawPluginApi } from 'openclaw/plugin-sdk';
import { registerProjectScheduler } from './project-scheduler.js';

export function registerAllServices(api: OpenClawPluginApi): void {
  registerProjectScheduler(api);
}
