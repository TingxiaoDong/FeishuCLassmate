import type { OpenClawPluginApi } from 'openclaw/plugin-sdk';
import { z } from 'zod';
import { getConfigFromApi } from '../../config.js';
import { getFeishuClient } from '../../util/feishu-api.js';
import { getTableId } from '../../bitable/setup.js';
import { registerZodTool } from '../../util/register-tool.js';

const Input = z.object({
  topic: z.string().describe('本周关注主题'),
  related_works: z.string().describe('发现的相关工作,Markdown 格式'),
  insights: z.string().describe('潜在启发'),
  source_project_ids: z.array(z.string()).default([]),
});

const Output = z.object({
  ok: z.boolean(),
  report_id: z.string().optional(),
  week: z.string().optional(),
  error: z.string().optional(),
});

export function registerResearchPublish(api: OpenClawPluginApi): void {
  registerZodTool(api, {
    name: 'feishu_classmate_research_publish',
    description:
      '把一份自主研究报告写入 Research 表。周标签按当前 ISO week 自动生成。',
    inputSchema: Input,
    outputSchema: Output,
    async execute(input) {
      const cfg = getConfigFromApi(api);
      const client = getFeishuClient(cfg);
      const tableId = getTableId(cfg, 'research');

      const week = isoWeekString(new Date());
      const reportId = `rep_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 6)}`;

      const res = await client.createRecord(cfg.bitable.appToken, tableId, {
        report_id: reportId,
        week,
        topic: input.topic,
        related_works: input.related_works,
        insights: input.insights,
        source_projects: input.source_project_ids.join(','),
        created_at: Date.now(),
      });

      return res.ok
        ? { ok: true, report_id: reportId, week }
        : { ok: false, error: res.error };
    },
  });
}

/** "2026-W16" style ISO week label. */
function isoWeekString(d: Date): string {
  const target = new Date(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()));
  const dayNum = target.getUTCDay() || 7;
  target.setUTCDate(target.getUTCDate() + 4 - dayNum);
  const yearStart = new Date(Date.UTC(target.getUTCFullYear(), 0, 1));
  const week = Math.ceil(((target.getTime() - yearStart.getTime()) / 86_400_000 + 1) / 7);
  return `${target.getUTCFullYear()}-W${String(week).padStart(2, '0')}`;
}
