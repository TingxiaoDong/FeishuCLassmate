/**
 * Daily resident-asset patrol: Temi RFID-scans the lab, we diff against the
 * Equipment Bitable (moved / missing / unknown), update locations, and post
 * a summary to the broadcast chat. Skipped when temi.mockMode=true (a patrol
 * without the real robot would produce misleading diffs).
 */

import type { OpenClawPluginApi } from 'openclaw/plugin-sdk';
import { getConfigFromApi } from '../config.js';
import { getFeishuClient } from '../util/feishu-api.js';
import { getTableId } from '../bitable/setup.js';
import { scheduleCron } from '../util/cron.js';
import { temiClient } from '../tools/temi/client.js';

interface ScannedTag {
  tag_id: string;
  location_estimate: string;
  rssi: number;
}

export function registerEquipmentPatrol(api: OpenClawPluginApi): void {
  const run = async () => {
    const cfg = getConfigFromApi(api);

    if (cfg.temi.mockMode) {
      api.logger?.info?.('[classmate/equipment-patrol] skipped: temi.mockMode=true (needs real robot)');
      return;
    }
    if (!cfg.bitable.appToken || !cfg.bitable.tableIds?.equipment) {
      api.logger?.info?.('[classmate/equipment-patrol] skipped: bitable not yet set up');
      return;
    }

    const scan = await temiClient.post<{ tags: ScannedTag[] }>(cfg, '/rfid-scan', {});
    if (!scan.ok) {
      api.logger?.error?.(`[classmate/equipment-patrol] rfid-scan failed: ${scan.error}`);
      return;
    }
    const tags = scan.data?.tags ?? [];

    const client = getFeishuClient(cfg);
    const tableId = getTableId(cfg, 'equipment');
    const list = await client.listRecords(cfg.bitable.appToken, tableId, { pageSize: 200 });
    if (!list.ok) {
      api.logger?.error?.(`[classmate/equipment-patrol] list equipment failed: ${list.error}`);
      return;
    }

    const byTagId = new Map<string, { record_id: string; fields: Record<string, unknown> }>();
    for (const row of list.value) {
      const tagId = String(row.fields.equipment_id ?? '');
      if (tagId) byTagId.set(tagId, row);
    }

    const now = Date.now();
    const scannedTagIds = new Set(tags.map((t) => t.tag_id));
    let movedCount = 0;
    const unknownTags: string[] = [];

    for (const tag of tags) {
      const row = byTagId.get(tag.tag_id);
      if (!row) {
        unknownTags.push(tag.tag_id);
        continue;
      }
      const currentLoc = String(row.fields.location ?? '');
      const patch: Record<string, unknown> = { last_seen_at: now };
      if (currentLoc !== tag.location_estimate) {
        patch.location = tag.location_estimate;
        movedCount += 1;
      }
      const upd = await client.updateRecord(cfg.bitable.appToken, tableId, row.record_id, patch);
      if (!upd.ok) {
        api.logger?.warn?.(`[classmate/equipment-patrol] update ${tag.tag_id} failed: ${upd.error}`);
      }
    }

    const missing: string[] = [];
    for (const [tagId, row] of byTagId) {
      if (scannedTagIds.has(tagId)) continue;
      if (String(row.fields.state ?? '') === '在库') {
        missing.push(String(row.fields.name ?? tagId));
      }
    }

    const dateStr = new Date(now).toISOString().slice(0, 10);
    const summary =
      `📋 今日资产巡查 (${dateStr})\n` +
      `- 扫描成功: ${tags.length} 项\n` +
      `- 位置变动: ${movedCount} 项 (已自动更新)\n` +
      `- 未找到: ${missing.length} 项 (请检查)${missing.length ? ` — ${missing.join('、')}` : ''}\n` +
      `- 未登记 tag: ${unknownTags.length} 项${unknownTags.length ? ` — ${unknownTags.join(', ')}` : ''}`;

    if (cfg.labInfo.broadcastChatId) {
      const send = await client.sendText({
        receive_id: cfg.labInfo.broadcastChatId,
        receive_id_type: 'chat_id',
        text: summary,
      });
      if (!send.ok) {
        api.logger?.warn?.(`[classmate/equipment-patrol] broadcast failed: ${send.error}`);
      }
    } else {
      api.logger?.info?.(`[classmate/equipment-patrol] no broadcastChatId; summary:\n${summary}`);
    }
  };

  api.registerService?.({
    id: 'classmate-equipment-patrol',
    async start(){
      const cfg = getConfigFromApi(api);
      scheduleCron(cfg.schedules.equipmentPatrolCron, run);
      api.logger?.info?.(
        `[classmate/equipment-patrol] registered cron: ${cfg.schedules.equipmentPatrolCron}`,
      );
    },
  } as Parameters<NonNullable<OpenClawPluginApi['registerService']>>[0]);
}
