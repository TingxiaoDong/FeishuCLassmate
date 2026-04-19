import type { OpenClawPluginApi } from 'openclaw/plugin-sdk';
import { z } from 'zod';
import { getConfigFromApi } from '../../config.js';
import { temiClient } from './client.js';
import { registerZodTool } from '../../util/register-tool.js';

const Input = z.object({
  type: z
    .enum(['encourage', 'poke', 'applause', 'nod'])
    .describe('手势类型:encourage 鼓励 / poke 轻戳提醒 / applause 鼓掌 / nod 点头。'),
});

const Output = z.object({
  ok: z.boolean(),
  mock: z.boolean(),
  error: z.string().optional(),
});

export function registerTemiGesture(api: OpenClawPluginApi): void {
  registerZodTool(api, {
    name: 'feishu_classmate_temi_gesture',
    description: '让 Temi 执行一个物理手势(鼓励、轻戳、鼓掌、点头),用于非语言交互提示。',
    inputSchema: Input,
    outputSchema: Output,
    async execute(input) {
      const cfg = getConfigFromApi(api);
      const res = await temiClient.post(
        cfg,
        '/gesture',
        { type: input.type },
        { mockReturn: { ok: true }, timeoutMs: 10_000 },
      );
      return { ok: res.ok, mock: res.mock, error: res.error };
    },
  });
}
