import type { OpenClawPluginApi } from 'openclaw/plugin-sdk';
import { z } from 'zod';
import { getConfigFromApi } from '../../config.js';
import { getFeishuClient } from '../../util/feishu-api.js';
import { getTableId } from '../../bitable/setup.js';
import { registerZodTool } from '../../util/register-tool.js';

const Input = z.object({
  within_days: z.number().int().min(0).max(14).default(0).describe('0=今天,1=未来一天,以此类推'),
});

const Output = z.object({
  nodes: z.array(
    z.object({
      gantt_id: z.string(),
      project_id: z.string(),
      owner_open_id: z.string(),
      milestone: z.string(),
      due_date_iso: z.string(),
      status: z.string(),
      progress: z.number(),
    }),
  ),
});

/**
 * Used by the gantt-scheduler cron service.
 */
export function registerGanttListTodayNodes(api: OpenClawPluginApi): void {
  registerZodTool(api, {
    name: 'feishu_classmate_gantt_list_today_nodes',
    description: '列出今天(或未来 N 天内)到期的甘特节点。用于每日节点提醒。',
    inputSchema: Input,
    outputSchema: Output,
    async execute(input) {
      const cfg = getConfigFromApi(api);
      const client = getFeishuClient(cfg);
      const tableId = getTableId(cfg, 'gantt');

      const today = startOfDay(new Date());
      const upperBound = today + (input.within_days + 1) * 86_400_000;

      const res = await client.listRecords(cfg.bitable.appToken, tableId, {
        filter: `AND(CurrentValue.[due_date]>=${today}, CurrentValue.[due_date]<${upperBound}, CurrentValue.[status]!="完成")`,
      });
      if (!res.ok) return { nodes: [] };

      const nodes = res.value.map((r) => {
        const f = r.fields;
        const owner = Array.isArray(f.owner_open_id)
          ? // eslint-disable-next-line @typescript-eslint/no-explicit-any
            (f.owner_open_id as any[])[0]?.id ?? ''
          : '';
        const due = typeof f.due_date === 'number' ? f.due_date : Number(f.due_date ?? 0);
        return {
          gantt_id: String(f.gantt_id ?? ''),
          project_id: String(f.project_id ?? ''),
          owner_open_id: String(owner),
          milestone: String(f.milestone ?? ''),
          due_date_iso: new Date(due).toISOString().slice(0, 10),
          status: String(f.status ?? ''),
          progress: typeof f.progress === 'number' ? f.progress : 0,
        };
      });

      return { nodes };
    },
  });
}

function startOfDay(d: Date): number {
  const copy = new Date(d);
  copy.setHours(0, 0, 0, 0);
  return copy.getTime();
}
