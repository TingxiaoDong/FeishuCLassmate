import type { OpenClawPluginApi } from 'openclaw/plugin-sdk';
import { z } from 'zod';
import { getConfigFromApi } from '../../config.js';
import { getFeishuClient } from '../../util/feishu-api.js';
import { getTableId } from '../../bitable/setup.js';
import { registerZodTool } from '../../util/register-tool.js';

const Input = z.object({
  equipment_id: z.string(),
  observed_location: z.string().optional().describe('人工确认的归还位置'),
  observed_state: z.enum(['正常', '损坏']).default('正常'),
});

const Output = z.object({
  ok: z.boolean(),
  error: z.string().optional(),
  was_overdue: z.boolean().optional(),
});

export function registerEquipmentReturn(api: OpenClawPluginApi): void {
  registerZodTool(api, {
    name: 'feishu_classmate_equipment_return',
    description: '归还器材:清除借用人,更新状态为在库 / 维修,记录最近一次被看到的时间。',
    inputSchema: Input,
    outputSchema: Output,
    async execute(input) {
      const cfg = getConfigFromApi(api);
      const client = getFeishuClient(cfg);
      const tableId = getTableId(cfg, 'equipment');

      const list = await client.listRecords(cfg.bitable.appToken, tableId, {
        filter: `CurrentValue.[equipment_id]="${input.equipment_id}"`,
        pageSize: 1,
      });
      if (!list.ok) return { ok: false, error: list.error };
      const target = list.value[0];
      if (!target) return { ok: false, error: `equipment_id ${input.equipment_id} not found` };

      const expectedReturn = Number(target.fields.expected_return ?? 0);
      const wasOverdue = expectedReturn > 0 && Date.now() > expectedReturn;

      const newState = input.observed_state === '损坏' ? '维修' : '在库';
      const update = await client.updateRecord(cfg.bitable.appToken, tableId, target.record_id, {
        state: newState,
        borrower_open_id: [],
        borrow_at: null,
        expected_return: null,
        last_seen_at: Date.now(),
        location: input.observed_location ?? target.fields.location ?? '',
      });

      return update.ok
        ? { ok: true, was_overdue: wasOverdue }
        : { ok: false, error: update.error };
    },
  });
}
