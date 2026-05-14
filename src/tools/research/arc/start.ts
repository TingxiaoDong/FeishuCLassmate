/**
 * feishu_classmate_research_arc_start — hand a finalized research plan off to
 * AutoResearchClaw (ARC) to validate the idea via its 23-stage pipeline.
 *
 * ARC runs are long (minutes → hours), so this is async: it returns a run_id
 * immediately. Poll with `feishu_classmate_research_arc_status`, then collect
 * deliverables with `feishu_classmate_research_arc_fetch`.
 */

import type { OpenClawPluginApi } from 'openclaw/plugin-sdk';
import { z } from 'zod';
import { getConfigFromApi } from '../../../config.js';
import { arcClient } from './client.js';
import { registerZodTool } from '../../../util/register-tool.js';

const Input = z.object({
  topic: z
    .string()
    .min(4)
    .describe(
      '要验证的实验性 idea / 研究课题,会作为 ARC 的 --topic。建议用 research-collaboration-agent 产出的 Research Goal。',
    ),
  mode: z
    .enum(['auto', 'co-pilot'])
    .default('auto')
    .describe('auto = 全自动(--auto-approve);co-pilot = 关键节点人工介入'),
  hypothesis: z
    .string()
    .default('')
    .describe('可选:本次要验证的明确假设,便于回写到 research 表时追溯'),
  plan_doc_url: z
    .string()
    .default('')
    .describe('可选:研究计划所在的飞书 Doc 链接'),
});

const Output = z.object({
  ok: z.boolean(),
  mock: z.boolean(),
  run_id: z.string().optional(),
  status: z.string().optional(),
  error: z.string().optional(),
});

export function registerResearchArcStart(api: OpenClawPluginApi): void {
  registerZodTool(api, {
    name: 'feishu_classmate_research_arc_start',
    description:
      '把一个实验性 idea 交给 AutoResearchClaw 跑 23-stage 流水线做验证(真实文献+sandbox 实验+多 agent 审稿)。' +
      '异步:立即返回 run_id,之后用 _status 轮询、_fetch 取结果。未连接 sidecar(mockMode)时返回模拟 run。',
    inputSchema: Input,
    outputSchema: Output,
    async execute(input) {
      const cfg = getConfigFromApi(api);
      const res = await arcClient.post(cfg, '/runs', {
        topic: input.topic,
        mode: input.mode,
        hypothesis: input.hypothesis,
        plan_doc_url: input.plan_doc_url,
      });
      const data = res.data as { run_id?: string; status?: string } | undefined;
      return {
        ok: res.ok,
        mock: res.mock,
        run_id: data?.run_id,
        status: data?.status,
        error: res.error,
      };
    },
  });
}
