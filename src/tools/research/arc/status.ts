/**
 * feishu_classmate_research_arc_status — poll the status of an ARC run started
 * by `feishu_classmate_research_arc_start`.
 *
 * status ∈ queued | running | completed | failed. Once "completed", call
 * `feishu_classmate_research_arc_fetch` for the deliverables.
 */

import type { OpenClawPluginApi } from 'openclaw/plugin-sdk';
import { z } from 'zod';
import { getConfigFromApi } from '../../../config.js';
import { arcClient } from './client.js';
import { registerZodTool } from '../../../util/register-tool.js';

const Input = z.object({
  run_id: z.string().describe('feishu_classmate_research_arc_start 返回的 run_id'),
});

const Output = z.object({
  ok: z.boolean(),
  mock: z.boolean(),
  run_id: z.string().optional(),
  status: z.string().optional(),
  topic: z.string().optional(),
  mode: z.string().optional(),
  started_at: z.string().optional(),
  finished_at: z.string().optional(),
  return_code: z.number().nullable().optional(),
  log_tail: z.array(z.string()).default([]),
  error: z.string().optional(),
});

export function registerResearchArcStatus(api: OpenClawPluginApi): void {
  registerZodTool(api, {
    name: 'feishu_classmate_research_arc_status',
    description:
      '查询一个 ARC run 的状态(queued/running/completed/failed)。run 较长,建议有节制地轮询;' +
      'completed 后用 _fetch 取交付物。',
    inputSchema: Input,
    outputSchema: Output,
    async execute(input) {
      const cfg = getConfigFromApi(api);
      const res = await arcClient.get(cfg, `/runs/${encodeURIComponent(input.run_id)}`);
      if (!res.ok) {
        return { ok: false, mock: res.mock, run_id: input.run_id, log_tail: [], error: res.error };
      }
      const d = res.data as Record<string, unknown>;
      return {
        ok: true,
        mock: res.mock,
        run_id: String(d.run_id ?? input.run_id),
        status: d.status as string | undefined,
        topic: d.topic as string | undefined,
        mode: d.mode as string | undefined,
        started_at: d.started_at as string | undefined,
        finished_at: d.finished_at as string | undefined,
        return_code: (d.return_code as number | null | undefined) ?? null,
        log_tail: Array.isArray(d.log_tail) ? (d.log_tail as string[]) : [],
        error: d.error ? String(d.error) : undefined,
      };
    },
  });
}
