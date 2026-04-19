import type { OpenClawPluginApi } from 'openclaw/plugin-sdk';
import { z } from 'zod';
import { getConfigFromApi } from '../../config.js';
import { getFeishuClient } from '../../util/feishu-api.js';
import { getTableId } from '../../bitable/setup.js';
import { registerZodTool } from '../../util/register-tool.js';

const Input = z.object({
  equipment_id: z.string().describe('器材 ID 或 RFID tag_id'),
  borrower_open_id: z.string(),
  expected_return_iso: z.string().describe('预计归还日期 YYYY-MM-DD'),
  notes: z.string().optional(),
});

const Output = z.object({
  ok: z.boolean(),
  record_id: z.string().optional(),
  error: z.string().optional(),
});

export function registerEquipmentBorrow(api: OpenClawPluginApi): void {
  registerZodTool(api, {
    name: 'feishu_classmate_equipment_borrow',
    description: '登记一次器材借用:更新 Equipment 表 state=借出,记录借用人和预计归还日期。',
    inputSchema: Input,
    outputSchema: Output,
    async execute(input) {
      const cfg = getConfigFromApi(api);
      const client = getFeishuClient(cfg);
      const tableId = getTableId(cfg, 'equipment');

      // Look up the equipment row
      const list = await client.listRecords(cfg.bitable.appToken, tableId, {
        filter: `CurrentValue.[equipment_id]="${input.equipment_id}"`,
        pageSize: 1,
      });
      if (!list.ok) return { ok: false, error: list.error };
      const target = list.value[0];
      if (!target) return { ok: false, error: `equipment_id ${input.equipment_id} not found` };

      if (target.fields.state === '借出') {
        return { ok: false, error: '该器材当前已借出,请先归还。' };
      }

      const update = await client.updateRecord(cfg.bitable.appToken, tableId, target.record_id, {
        state: '借出',
        borrower_open_id: [{ id: input.borrower_open_id }],
        borrow_at: Date.now(),
        expected_return: Date.parse(input.expected_return_iso),
        notes: input.notes ?? '',
      });

      return update.ok
        ? { ok: true, record_id: target.record_id }
        : { ok: false, error: update.error };
    },
  });
}
