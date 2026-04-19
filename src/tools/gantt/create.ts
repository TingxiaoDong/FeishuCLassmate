import type { OpenClawPluginApi } from 'openclaw/plugin-sdk';
import { z } from 'zod';
import { getConfigFromApi } from '../../config.js';
import { getFeishuClient } from '../../util/feishu-api.js';
import { getTableId } from '../../bitable/setup.js';
import { registerZodTool } from '../../util/register-tool.js';

const CreateInput = z.object({
  project_id: z.string(),
  owner_open_id: z.string(),
  milestones: z
    .array(
      z.object({
        milestone: z.string(),
        due_date_iso: z.string().describe('YYYY-MM-DD'),
      }),
    )
    .min(1),
});

const CreateOutput = z.object({
  ok: z.boolean(),
  gantt_ids: z.array(z.string()),
  record_ids: z.array(z.string()),
  error: z.string().optional(),
});

export function registerGanttCreate(api: OpenClawPluginApi): void {
  registerZodTool(api, {
    name: 'feishu_classmate_gantt_create',
    description: '为一个项目批量写入甘特图节点 (milestones)。',
    inputSchema: CreateInput,
    outputSchema: CreateOutput,
    async execute(input) {
      const cfg = getConfigFromApi(api);
      const client = getFeishuClient(cfg);
      const tableId = getTableId(cfg, 'gantt');

      const records: Array<Record<string, unknown>> = [];
      const ganttIds: string[] = [];

      for (const m of input.milestones) {
        const id = `g_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 6)}`;
        ganttIds.push(id);
        records.push({
          gantt_id: id,
          project_id: input.project_id,
          owner_open_id: [{ id: input.owner_open_id }],
          milestone: m.milestone,
          due_date: Date.parse(m.due_date_iso),
          progress: 0,
          status: '未开始',
          notes: '',
        });
      }

      const res = await client.batchCreateRecords(cfg.bitable.appToken, tableId, records);
      if (!res.ok) {
        return { ok: false, gantt_ids: [], record_ids: [], error: res.error };
      }
      return { ok: true, gantt_ids: ganttIds, record_ids: res.value.record_ids };
    },
  });
}
