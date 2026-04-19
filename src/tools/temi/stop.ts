import type { OpenClawPluginApi } from 'openclaw/plugin-sdk';
import { z } from 'zod';
import { getConfigFromApi } from '../../config.js';
import { temiClient } from './client.js';
import { registerZodTool } from '../../util/register-tool.js';

const Input = z.object({
  immediate: z.boolean().default(false),
});

const Output = z.object({
  ok: z.boolean(),
  mock: z.boolean(),
  error: z.string().optional(),
});

export function registerTemiStop(api: OpenClawPluginApi): void {
  registerZodTool(api, {
    name: 'feishu_classmate_temi_stop',
    description: '立即停止 Temi 的所有动作(紧急停止或优雅停止)。',
    inputSchema: Input,
    outputSchema: Output,
    async execute(input) {
      const cfg = getConfigFromApi(api);
      const res = await temiClient.post(
        cfg,
        '/stop',
        { immediate: input.immediate },
        { mockReturn: { ok: true } },
      );
      return { ok: res.ok, mock: res.mock, error: res.error };
    },
  });
}
