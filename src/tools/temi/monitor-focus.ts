import type { OpenClawPluginApi } from 'openclaw/plugin-sdk';
import { z } from 'zod';
import { getConfigFromApi } from '../../config.js';
import { temiClient } from './client.js';
import { registerZodTool } from '../../util/register-tool.js';

const Input = z.object({
  student_open_id: z.string(),
  duration_s: z
    .number()
    .int()
    .min(30)
    .max(3600)
    .describe('监控时长(秒),范围 30-3600。'),
});

const FocusSample = z.object({
  ts: z.number(),
  focused: z.boolean(),
  score: z.number(),
});

const Output = z.object({
  ok: z.boolean(),
  mock: z.boolean(),
  samples: z.array(FocusSample),
  error: z.string().optional(),
});

export function registerTemiMonitorFocus(api: OpenClawPluginApi): void {
  registerZodTool(api, {
    name: 'feishu_classmate_temi_monitor_focus',
    description:
      '让 Temi 通过摄像头监控指定学生的专注度 duration_s 秒,返回周期性采样点。' +
      'mockMode 下 sidecar 生成真实感的专注曲线(高 → 中段下降 → 恢复)。',
    inputSchema: Input,
    outputSchema: Output,
    async execute(input) {
      const cfg = getConfigFromApi(api);
      const res = await temiClient.post<{ samples: Array<{ ts: number; focused: boolean; score: number }> }>(
        cfg,
        '/monitor-focus',
        { student_open_id: input.student_open_id, duration_s: input.duration_s },
        {
          timeoutMs: input.duration_s * 1000 + 5000,
          mockReturn: { samples: [] }, // sidecar generates real mock data
        },
      );
      return {
        ok: res.ok,
        mock: res.mock,
        samples: res.data?.samples ?? [],
        error: res.error,
      };
    },
  });
}
