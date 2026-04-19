import type { OpenClawPluginApi } from 'openclaw/plugin-sdk';
import { registerGanttCreate } from './create.js';
import { registerGanttUpdateProgress } from './update-progress.js';
import { registerGanttListTodayNodes } from './list-today-nodes.js';

export function registerGanttTools(api: OpenClawPluginApi): void {
  registerGanttCreate(api);
  registerGanttUpdateProgress(api);
  registerGanttListTodayNodes(api);
}
