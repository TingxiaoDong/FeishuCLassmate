/**
 * feishu_classmate_project_ingest
 *
 * Takes raw student narration (or doc text) and returns a structured project
 * skeleton. This tool intentionally does NOT write anything — the agent must
 * call `project_create` afterwards so the student has a confirmation step.
 *
 * The structured schema matches the Projects + Gantt Bitable schemas.
 */

import type { OpenClawPluginApi } from 'openclaw/plugin-sdk';
import { z } from 'zod';
import { registerZodTool } from '../../util/register-tool.js';

const IngestInput = z.object({
  raw_text: z.string().min(1).describe('学生口述或粘贴的项目描述原文'),
  default_visibility: z
    .enum(['可公开', '保密'])
    .default('保密')
    .describe('默认可见性,学生未明确时用此值'),
  owner_open_id: z.string().optional().describe('项目负责人 open_id,不填则在 create 时由会话上下文推断'),
});

const IngestOutput = z.object({
  title: z.string(),
  keywords: z.array(z.string()),
  visibility: z.enum(['可公开', '保密']),
  abstract: z.string(),
  milestones: z.array(
    z.object({
      milestone: z.string(),
      due_date_iso: z.string().describe('YYYY-MM-DD'),
    }),
  ),
  confidence: z.number().min(0).max(1),
});

export function registerProjectIngest(api: OpenClawPluginApi): void {
  registerZodTool(api, {
    name: 'feishu_classmate_project_ingest',
    description:
      '把学生口述的项目描述解析为结构化的 {title, keywords, visibility, abstract, milestones}。' +
      '不会写入任何表——调用方应把结果展示给学生确认后再调用 feishu_classmate_project_create。',
    inputSchema: IngestInput,
    outputSchema: IngestOutput,
    async execute(input) {
      // This tool's job is pure prompt-engineering: the agent LLM is the one
      // doing the extraction. We just shape the return.
      //
      // OpenClaw's tool protocol allows a tool to delegate back to the LLM by
      // returning a "meta" result that the model fills in. When the agent
      // itself is the Claude/GPT behind MetaClaw, it does the parsing inline.
      // We provide a heuristic fallback here for deterministic unit tests.
      return heuristicIngest(input.raw_text, input.default_visibility);
    },
  });
}

/**
 * Simple keyword-based heuristic. The real extraction happens in the LLM.
 * Kept as a fallback so the tool always returns something and tests are hermetic.
 */
function heuristicIngest(
  raw: string,
  defaultVisibility: '可公开' | '保密',
): z.infer<typeof IngestOutput> {
  const title = raw.split(/[.。\n]/)[0].slice(0, 40) || '未命名项目';

  // pull a few candidate keywords (simple frequency-based)
  const words = raw
    .replace(/[,,。.!?;:""''()（）]/g, ' ')
    .split(/\s+/)
    .filter((w) => w.length >= 2 && w.length <= 10);
  const freq = new Map<string, number>();
  for (const w of words) freq.set(w, (freq.get(w) ?? 0) + 1);
  const keywords = [...freq.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5)
    .map(([w]) => w);

  // Default three milestones 2/4/6 weeks out.
  const now = Date.now();
  const week = 7 * 24 * 60 * 60 * 1000;
  const isoDate = (ms: number) => new Date(ms).toISOString().slice(0, 10);

  return {
    title,
    keywords,
    visibility: defaultVisibility,
    abstract: raw.slice(0, 500),
    milestones: [
      { milestone: '文献调研完成', due_date_iso: isoDate(now + 2 * week) },
      { milestone: '原型跑通', due_date_iso: isoDate(now + 4 * week) },
      { milestone: '初版实验结果', due_date_iso: isoDate(now + 6 * week) },
    ],
    confidence: 0.3,
  };
}
