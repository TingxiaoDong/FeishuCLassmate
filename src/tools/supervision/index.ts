import type { OpenClawPluginApi } from 'openclaw/plugin-sdk';
import { registerSupervisionStart } from './start.js';
import { registerSupervisionTick } from './tick.js';
import { registerSupervisionSummarize } from './summarize.js';

export function registerSupervisionTools(api: OpenClawPluginApi): void {
  registerSupervisionStart(api);
  registerSupervisionTick(api);
  registerSupervisionSummarize(api);
}

export {
  getSupervisionSessions,
  getSupervisionSession,
  recordSupervisionNote,
  endSupervisionSession,
} from './start.js';
