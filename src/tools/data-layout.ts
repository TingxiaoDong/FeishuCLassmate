/**
 * feishu_classmate_data_layout
 *
 * Returns the Bitable app_token, table_ids and expected field layout so the
 * agent can call `feishu_bitable_app_table_record` / `feishu_bitable_app_table_field`
 * from @larksuite/openclaw-lark directly.
 */

import type { OpenClawPluginApi } from 'openclaw/plugin-sdk';
import { z } from 'zod';
import { getConfigFromApi } from '../config.js';
import { ALL_TABLES } from '../bitable/schema.js';
import { registerZodTool } from '../util/register-tool.js';

const Output = z.object({
  app_token: z.string(),
  tables: z.record(
    z.string(),
    z.object({
      table_id: z.string(),
      fields: z.array(
        z.object({
          name: z.string(),
          type: z.number().describe(
            'Bitable field type: 1=Text, 2=Number, 3=SingleSelect, 4=MultiSelect, 5=DateTime, 11=User, 15=Url, 17=Attachment',
          ),
          options: z.array(z.string()).optional().describe('For SingleSelect/MultiSelect fields'),
        }),
      ),
    }),
  ),
  notes: z.string(),
});

export function registerDataLayout(api: OpenClawPluginApi): void {
  registerZodTool(api, {
    name: 'feishu_classmate_data_layout',
    description:
      '返回飞书同学四张多维表的 app_token、table_id 和字段清单。Agent 应先调此 tool,' +
      '再用 @larksuite/openclaw-lark 提供的 feishu_bitable_app_table_record / feishu_bitable_app_table_field 去读写,' +
      '不要绕过多维表自己造数据。',
    inputSchema: z.object({}),
    outputSchema: Output,
    async execute() {
      const cfg = getConfigFromApi(api);
      const tables: Record<string, { table_id: string; fields: Array<{ name: string; type: number; options?: string[] }> }> = {};

      for (const def of ALL_TABLES) {
        const tid = cfg.bitable.tableIds?.[def.key as 'projects' | 'gantt' | 'equipment' | 'research'];
        if (!tid) continue;
        tables[def.key] = {
          table_id: tid,
          fields: def.fields.map((f) => ({
            name: f.field_name,
            type: f.type,
            options: extractOptions(f.property),
          })),
        };
      }

      return {
        app_token: cfg.bitable.appToken,
        tables,
        notes: [
          '使用 @larksuite/openclaw-lark 的 feishu_bitable_app_table_record 直接读写记录。',
          '人员 (User, type=11) 字段值格式: [{"id": "ou_xxx"}]。',
          '日期 (DateTime, type=5) 字段值: 毫秒时间戳(number)。',
          'SingleSelect (type=3) 字段值: 必须严格用 options 里列出的字符串之一。',
          'MultiSelect (type=4) 字段值: 字符串数组,每项必须是 options 之一。',
          '写新记录前先用 feishu_bitable_app_table_field 的 list action 核对字段类型,再用 record 的 create action。',
        ].join(' '),
      };
    },
  });
}

function extractOptions(property: unknown): string[] | undefined {
  if (!property || typeof property !== 'object') return undefined;
  const p = property as { options?: Array<{ name: string }> };
  if (!Array.isArray(p.options)) return undefined;
  return p.options.map((o) => o.name).filter(Boolean);
}
