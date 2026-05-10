import type { OpenClawPluginApi } from 'openclaw/plugin-sdk';
import { z } from 'zod';
import { getConfigFromApi } from '../../config.js';
import { temiClient } from './client.js';
import { registerZodTool } from '../../util/register-tool.js';

const Input = z.object({});

const Output = z.object({
  ok: z.boolean(),
  mock: z.boolean(),
  error: z.string().optional(),
});

/**
 * Wakes Temi / WOZ into interaction mode so onboard ASR can run.
 * When `TEMI_ASR_WEBHOOK_URL` is set on the sidecar, recognized speech is POSTed to the backend.
 */
export function registerTemiWakeup(api: OpenClawPluginApi): void {
  registerZodTool(api, {
    name: 'feishu_classmate_temi_wakeup',
    description:
      '唤醒 Temi 进入语音交互状态(对接 WOZ)。同学说话后,若 sidecar 配置了 TEMI_ASR_WEBHOOK_URL,识别结果会 POST 到后台;不用于播报。',
    inputSchema: Input,
    outputSchema: Output,
    async execute() {
      const cfg = getConfigFromApi(api);
      const res = await temiClient.post(cfg, '/wakeup', {}, { mockReturn: { ok: true, mock: true } });
      const data = (res.data ?? {}) as { ok?: boolean; mock?: boolean; error?: string };
      return {
        ok: res.ok && data.ok !== false,
        mock: res.mock || Boolean(data.mock),
        error: res.error ?? (typeof data.error === 'string' ? data.error : undefined),
      };
    },
  });
}
