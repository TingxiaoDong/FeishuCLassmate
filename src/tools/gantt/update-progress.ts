import type { OpenClawPluginApi } from 'openclaw/plugin-sdk';
import { z } from 'zod';
import { getConfigFromApi } from '../../config.js';
import { getFeishuClient } from '../../util/feishu-api.js';
import { getTableId } from '../../bitable/setup.js';
import { registerZodTool } from '../../util/register-tool.js';

const Input = z.object({
  gantt_id: z.string(),
  progress: z.number().min(0).max(100),
  notes: z.string().optional(),
  status: z.enum(['未开始', '进行中', '完成', '逾期']).optional(),
});

const Output = z.object({
  ok: z.boolean(),
  error: z.string().optional(),
});

export function registerGanttUpdateProgress(api: OpenClawPluginApi): void {
  registerZodTool(api, {
    name: 'feishu_classmate_gantt_update_progress',
    description: '更新某个甘特节点的进度 / 备注 / 状态。',
    inputSchema: Input,
    outputSchema: Output,
    async execute(input) {
      const cfg = getConfigFromApi(api);
      const client = getFeishuClient(cfg);
      const tableId = getTableId(cfg, 'gantt');

      // Find the record by gantt_id
      const list = await client.listRecords(cfg.bitable.appToken, tableId, {
        filter: `CurrentValue.[gantt_id]="${input.gantt_id}"`,
        pageSize: 1,
      });
      if (!list.ok) return { ok: false, error: list.error };
      const target = list.value[0];
      if (!target) return { ok: false, error: `gantt_id ${input.gantt_id} not found` };

      const updateFields: Record<string, unknown> = {
        progress: input.progress,
      };
      if (input.notes !== undefined) updateFields.notes = input.notes;
      if (input.status !== undefined) updateFields.status = input.status;

      // Auto-upgrade status based on progress if the caller didn't set it.
      if (input.status === undefined) {
        if (input.progress >= 100) updateFields.status = '完成';
        else if (input.progress > 0) updateFields.status = '进行中';
      }

      const r = await client.updateRecord(
        cfg.bitable.appToken,
        tableId,
        target.record_id,
        updateFields,
      );
      return r.ok ? { ok: true } : { ok: false, error: r.error };
    },
  });
}
