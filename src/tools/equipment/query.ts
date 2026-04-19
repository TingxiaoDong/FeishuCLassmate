import type { OpenClawPluginApi } from 'openclaw/plugin-sdk';
import { z } from 'zod';
import { getConfigFromApi } from '../../config.js';
import { getFeishuClient } from '../../util/feishu-api.js';
import { getTableId } from '../../bitable/setup.js';
import { registerZodTool } from '../../util/register-tool.js';

const Input = z.object({
  name: z.string().optional().describe('器材名称模糊匹配'),
  state: z.enum(['在库', '借出', '维修', '丢失']).optional(),
});

const Output = z.object({
  rows: z.array(
    z.object({
      equipment_id: z.string(),
      name: z.string(),
      location: z.string(),
      state: z.string(),
      borrower_open_id: z.string().optional(),
    }),
  ),
});

export function registerEquipmentQuery(api: OpenClawPluginApi): void {
  registerZodTool(api, {
    name: 'feishu_classmate_equipment_query',
    description: '按名称或状态查询器材库存。',
    inputSchema: Input,
    outputSchema: Output,
    async execute(input) {
      const cfg = getConfigFromApi(api);
      const client = getFeishuClient(cfg);
      const tableId = getTableId(cfg, 'equipment');

      const filters: string[] = [];
      if (input.name) filters.push(`CurrentValue.[name].contains("${input.name}")`);
      if (input.state) filters.push(`CurrentValue.[state]="${input.state}"`);
      const filter = filters.length ? `AND(${filters.join(',')})` : undefined;

      const res = await client.listRecords(cfg.bitable.appToken, tableId, { filter });
      if (!res.ok) return { rows: [] };

      const rows = res.value.map((r) => {
        const f = r.fields;
        const borrower = Array.isArray(f.borrower_open_id)
          ? // eslint-disable-next-line @typescript-eslint/no-explicit-any
            (f.borrower_open_id as any[])[0]?.id ?? undefined
          : undefined;
        return {
          equipment_id: String(f.equipment_id ?? ''),
          name: String(f.name ?? ''),
          location: String(f.location ?? ''),
          state: String(f.state ?? ''),
          borrower_open_id: borrower,
        };
      });
      return { rows };
    },
  });
}
