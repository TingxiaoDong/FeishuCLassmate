/**
 * feishu_classmate_research_arc_fetch — fetch the deliverables of a completed
 * ARC run: paper draft, LaTeX, references, peer reviews, charts, experiments.
 *
 * The agent then writes these back into Feishu (the `research` Bitable table
 * + a Feishu Doc) as the validation artifact for the lab's idea.
 */

import type { OpenClawPluginApi } from 'openclaw/plugin-sdk';
import { z } from 'zod';
import { getConfigFromApi } from '../../../config.js';
import { arcClient } from './client.js';
import { registerZodTool } from '../../../util/register-tool.js';

const Input = z.object({
  run_id: z.string().describe('feishu_classmate_research_arc_start 返回的 run_id'),
});

const FileEntry = z.object({
  path: z.string(),
  bytes: z.number().optional(),
  preview: z.string().optional(),
});

const DirEntry = z.object({
  path: z.string(),
  count: z.number(),
  children: z.array(z.string()).default([]),
});

const Output = z.object({
  ok: z.boolean(),
  mock: z.boolean(),
  run_id: z.string().optional(),
  status: z.string().optional(),
  workdir: z.string().optional(),
  // Known deliverable files: paper_draft / paper_tex / references_bib /
  // verification_report / reviews — each with path + (for text) a preview.
  files: z.record(z.string(), FileEntry).default({}),
  // Known deliverable dirs: charts / experiments / evolution / deliverables.
  dirs: z.record(z.string(), DirEntry).default({}),
  note: z.string().optional(),
  error: z.string().optional(),
});

export function registerResearchArcFetch(api: OpenClawPluginApi): void {
  registerZodTool(api, {
    name: 'feishu_classmate_research_arc_fetch',
    description:
      '取一个已完成 ARC run 的交付物(paper_draft/paper.tex/references.bib/reviews/charts/experiments 等),' +
      '附文本类文件的预览片段。run 未完成时只返回当前状态。拿到后应回写 research 多维表 + 飞书 Doc。',
    inputSchema: Input,
    outputSchema: Output,
    async execute(input) {
      const cfg = getConfigFromApi(api);
      const res = await arcClient.get(cfg, `/runs/${encodeURIComponent(input.run_id)}/result`);
      if (!res.ok) {
        return { ok: false, mock: res.mock, run_id: input.run_id, files: {}, dirs: {}, error: res.error };
      }
      const d = res.data as Record<string, unknown>;
      const status = d.status as string | undefined;
      const deliverables = d.deliverables as
        | { workdir?: string; files?: Record<string, unknown>; dirs?: Record<string, unknown> }
        | null
        | undefined;

      if (!deliverables) {
        return {
          ok: true,
          mock: res.mock,
          run_id: String(d.run_id ?? input.run_id),
          status,
          files: {},
          dirs: {},
          note: `run 尚未完成(status=${status ?? 'unknown'}),暂无交付物`,
          error: d.error ? String(d.error) : undefined,
        };
      }

      return {
        ok: true,
        mock: res.mock,
        run_id: String(d.run_id ?? input.run_id),
        status,
        workdir: deliverables.workdir,
        files: (deliverables.files ?? {}) as z.infer<typeof Output>['files'],
        dirs: (deliverables.dirs ?? {}) as z.infer<typeof Output>['dirs'],
      };
    },
  });
}
