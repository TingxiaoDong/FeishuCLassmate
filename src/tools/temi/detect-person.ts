import type { OpenClawPluginApi } from 'openclaw/plugin-sdk';
import { z } from 'zod';
import { getConfigFromApi } from '../../config.js';
import { temiClient } from './client.js';
import { registerZodTool } from '../../util/register-tool.js';

const Input = z.object({
  timeout_ms: z.number().int().min(500).max(15_000).default(5_000),
});

const Output = z.object({
  ok: z.boolean(),
  mock: z.boolean(),
  open_id: z.string().nullable(),
  confidence: z.number().min(0).max(1),
  error: z.string().optional(),
});

export function registerTemiDetectPerson(api: OpenClawPluginApi): void {
  registerZodTool(api, {
    name: 'feishu_classmate_temi_detect_person',
    description:
      '通过 Temi 摄像头识别画面内学生的 open_id。未识别到返回 null。mock 模式下永远返回 null。',
    inputSchema: Input,
    outputSchema: Output,
    async execute(input) {
      const cfg = getConfigFromApi(api);
      const res = await temiClient.post(
        cfg,
        '/detect-person',
        { timeout_ms: input.timeout_ms },
        { mockReturn: { open_id: null, confidence: 0 } },
      );
      const data = (res.data ?? {}) as { open_id?: string | null; confidence?: number };
      return {
        ok: res.ok,
        mock: res.mock,
        open_id: data.open_id ?? null,
        confidence: data.confidence ?? 0,
        error: res.error,
      };
    },
  });
}
