import type { OpenClawPluginApi } from 'openclaw/plugin-sdk';
import { registerTemiNavigateTo } from './navigate-to.js';
import { registerTemiSpeak } from './speak.js';
import { registerTemiStop } from './stop.js';
import { registerTemiDetectPerson } from './detect-person.js';
import { registerTemiStatus } from './status.js';
import { registerTemiRfidScan } from './rfid-scan.js';
import { registerTemiMonitorFocus } from './monitor-focus.js';
import { registerTemiGesture } from './gesture.js';
import { registerTemiControl } from './control.js';

export function registerTemiTools(api: OpenClawPluginApi): void {
  registerTemiNavigateTo(api);
  registerTemiSpeak(api);
  registerTemiStop(api);
  registerTemiDetectPerson(api);
  registerTemiStatus(api);
  registerTemiRfidScan(api);
  registerTemiMonitorFocus(api);
  registerTemiGesture(api);
  registerTemiControl(api);
}
