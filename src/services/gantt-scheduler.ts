/**
 * Daily Gantt node reminder service.
 *
 * Every morning (per config.schedules.ganttCheckCron):
 *   1. List today's milestones (via direct Bitable query).
 *   2. For each milestone, DM the owner with an interactive prompt.
 *   3. (TODO Phase 1 follow-up) Capture the student's reply via inbound hook
 *      and call gantt_update_progress.
 */

import type { OpenClawPluginApi } from 'openclaw/plugin-sdk';
import { getConfigFromApi } from '../config.js';
import { getFeishuClient } from '../util/feishu-api.js';
import { getTableId } from '../bitable/setup.js';
import { scheduleCron } from '../util/cron.js';

export function registerGanttScheduler(api: OpenClawPluginApi): void {
  const run = async () => {
    const cfg = getConfigFromApi(api);
    if (!cfg.bitable.appToken || !cfg.bitable.tableIds?.gantt) {
      api.logger?.info?.('[classmate/gantt-scheduler] skipped: bitable not yet set up');
      return;
    }

    const client = getFeishuClient(cfg);
    const tableId = getTableId(cfg, 'gantt');
    const today = startOfDay(new Date());
    const tomorrow = today + 86_400_000;

    const list = await client.listRecords(cfg.bitable.appToken, tableId, {
      filter: `AND(CurrentValue.[due_date]>=${today}, CurrentValue.[due_date]<${tomorrow}, CurrentValue.[status]!="完成")`,
    });
    if (!list.ok) {
      api.logger?.error?.(`[classmate/gantt-scheduler] list failed: ${list.error}`);
      return;
    }

    if (list.value.length === 0) {
      api.logger?.info?.('[classmate/gantt-scheduler] no nodes due today');
      return;
    }

    for (const row of list.value) {
      const f = row.fields;
      const owner = Array.isArray(f.owner_open_id)
        ? // eslint-disable-next-line @typescript-eslint/no-explicit-any
          (f.owner_open_id as any[])[0]?.id
        : undefined;
      if (!owner) continue;

      const milestone = String(f.milestone ?? '');
      const ganttId = String(f.gantt_id ?? '');
      const projectId = String(f.project_id ?? '');

      const text =
        `📅 今天是【${milestone}】的计划完成日。\n` +
        `项目: ${projectId}\n` +
        `请回复进度 (0-100)、当前状态和卡点,我会帮你更新甘特图。\n` +
        `(gantt_id=${ganttId})`;

      const send = await client.sendText({
        receive_id: owner,
        receive_id_type: 'open_id',
        text,
      });
      if (!send.ok) {
        api.logger?.warn?.(`[classmate/gantt-scheduler] send to ${owner} failed: ${send.error}`);
      }
    }

    api.logger?.info?.(
      `[classmate/gantt-scheduler] pinged ${list.value.length} students for today's milestones`,
    );
  };

  api.registerService?.({
    id: 'classmate-gantt-scheduler',
    async start(){
      const cfg = getConfigFromApi(api);
      scheduleCron(cfg.schedules.ganttCheckCron, run);
      api.logger?.info?.(
        `[classmate/gantt-scheduler] registered cron: ${cfg.schedules.ganttCheckCron}`,
      );
    },
  } as Parameters<NonNullable<OpenClawPluginApi['registerService']>>[0]);
}

function startOfDay(d: Date): number {
  const copy = new Date(d);
  copy.setHours(0, 0, 0, 0);
  return copy.getTime();
}
