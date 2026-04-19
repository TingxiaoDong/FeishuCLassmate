import type { OpenClawPluginApi } from 'openclaw/plugin-sdk';
import { z } from 'zod';
import { getConfigFromApi } from '../../config.js';
import { temiClient } from './client.js';
import { registerZodTool } from '../../util/register-tool.js';

const Input = z.object({
  text: z.string().min(1).max(500),
  voice: z.enum(['friendly', 'professional']).default('friendly'),
});

const Output = z.object({
  ok: z.boolean(),
  mock: z.boolean(),
  error: z.string().optional(),
});

export function registerTemiSpeak(api: OpenClawPluginApi): void {
  registerZodTool(api, {
    name: 'feishu_classmate_temi_speak',
    description: 'Temi TTS 朗读一段文字。',
    inputSchema: Input,
    outputSchema: Output,
    async execute(input) {
      const cfg = getConfigFromApi(api);
      const res = await temiClient.post(
        cfg,
        '/speak',
        { text: input.text, voice: input.voice },
        { mockReturn: { ok: true, note: `(模拟)说: ${input.text}` }, timeoutMs: 30_000 },
      );
      return { ok: res.ok, mock: res.mock, error: res.error };
    },
  });
}
