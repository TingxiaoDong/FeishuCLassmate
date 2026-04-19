import type { OpenClawPluginApi } from 'openclaw/plugin-sdk';
import { registerGanttScheduler } from './gantt-scheduler.js';
import { registerIdleLoop } from './idle-loop.js';
import { registerEquipmentPatrol } from './equipment-patrol.js';
import { registerSupervisionTicker } from './supervision-ticker.js';

export function registerAllServices(api: OpenClawPluginApi): void {
  registerGanttScheduler(api);
  registerIdleLoop(api);
  registerEquipmentPatrol(api);
  registerSupervisionTicker(api);
}
