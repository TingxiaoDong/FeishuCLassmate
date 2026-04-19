import type { OpenClawPluginApi } from 'openclaw/plugin-sdk';
import { registerEquipmentQuery } from './query.js';
import { registerEquipmentBorrow } from './borrow.js';
import { registerEquipmentReturn } from './return.js';

export function registerEquipmentTools(api: OpenClawPluginApi): void {
  registerEquipmentQuery(api);
  registerEquipmentBorrow(api);
  registerEquipmentReturn(api);
}
