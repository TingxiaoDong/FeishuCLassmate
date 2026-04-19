/**
 * feishu_classmate_research_pick_topic — pick a weekly research topic by
 * scanning Projects keywords and avoiding topics covered in the last 2 weeks.
 */

import type { OpenClawPluginApi } from 'openclaw/plugin-sdk';
import { z } from 'zod';
import { getConfigFromApi } from '../../config.js';
import { getFeishuClient } from '../../util/feishu-api.js';
import { getTableId } from '../../bitable/setup.js';
import { registerZodTool } from '../../util/register-tool.js';

const Input = z.object({
  max_keywords: z.number().int().min(1).max(20).default(5),
});

const Output = z.object({
  ok: z.boolean(),
  topic: z.string().optional(),
  source_project_ids: z.array(z.string()).default([]),
  rationale: z.string().optional(),
  error: z.string().optional(),
});

const TWO_WEEKS_MS = 14 * 24 * 3_600_000;

export function registerResearchPickTopic(api: OpenClawPluginApi): void {
  registerZodTool(api, {
    name: 'feishu_classmate_research_pick_topic',
    description:
      '扫描 Projects 表的 keywords 频次,过滤掉最近 2 周 Research 表已写过的 topic,返回最热的一个关键词作为本周研究主题。',
    inputSchema: Input,
    outputSchema: Output,
    async execute(input) {
      const cfg = getConfigFromApi(api);
      const client = getFeishuClient(cfg);

      let projectsTableId: string;
      let researchTableId: string;
      try {
        projectsTableId = getTableId(cfg, 'projects');
        researchTableId = getTableId(cfg, 'research');
      } catch (err) {
        return { ok: false, source_project_ids: [], error: String(err instanceof Error ? err.message : err) };
      }

      const projectsRes = await client.listRecords(cfg.bitable.appToken, projectsTableId, { pageSize: 200 });
      if (!projectsRes.ok) {
        return { ok: false, source_project_ids: [], error: `list projects failed: ${projectsRes.error}` };
      }

      // Tally keyword frequency and remember which projects referenced each.
      const freq = new Map<string, number>();
      const byKeyword = new Map<string, string[]>();
      for (const row of projectsRes.value) {
        const f = row.fields;
        const keywords = extractMultiSelect(f.keywords);
        const projectId = typeof f.project_id === 'string' ? f.project_id : row.record_id;
        for (const kw of keywords) {
          freq.set(kw, (freq.get(kw) ?? 0) + 1);
          const ids = byKeyword.get(kw) ?? [];
          if (!ids.includes(projectId)) ids.push(projectId);
          byKeyword.set(kw, ids);
        }
      }

      // Fetch recent Research rows to exclude already-covered topics.
      const researchRes = await client.listRecords(cfg.bitable.appToken, researchTableId, { pageSize: 100 });
      const recentTopics = new Set<string>();
      if (researchRes.ok) {
        const cutoff = Date.now() - TWO_WEEKS_MS;
        for (const row of researchRes.value) {
          const f = row.fields;
          const createdAt = typeof f.created_at === 'number' ? f.created_at : 0;
          const topic = typeof f.topic === 'string' ? f.topic : '';
          if (topic && createdAt >= cutoff) recentTopics.add(topic.toLowerCase());
        }
      }

      // Rank candidates by frequency, skip recent.
      const ranked = [...freq.entries()]
        .filter(([kw]) => !recentTopics.has(kw.toLowerCase()))
        .sort((a, b) => b[1] - a[1])
        .slice(0, input.max_keywords);

      if (ranked.length === 0) {
        return {
          ok: false,
          source_project_ids: [],
          error: '没有候选关键词(或最近 2 周已覆盖所有热点)',
        };
      }

      const [topic, count] = ranked[0];
      const sourceIds = byKeyword.get(topic) ?? [];
      const rationale = `${count} 个项目引用了「${topic}」;过去 2 周无相关 Research 报告`;

      return {
        ok: true,
        topic,
        source_project_ids: sourceIds,
        rationale,
      };
    },
  });
}

/** Bitable MultiSelect fields come back as string[] — tolerate the odd shape. */
function extractMultiSelect(val: unknown): string[] {
  if (!val) return [];
  if (Array.isArray(val)) {
    return val.filter((x): x is string => typeof x === 'string' && x.length > 0);
  }
  if (typeof val === 'string' && val.length > 0) return [val];
  return [];
}
