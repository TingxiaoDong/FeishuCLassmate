import type { OpenClawPluginApi } from 'openclaw/plugin-sdk';
import { z } from 'zod';
import { getConfigFromApi } from '../../config.js';
import { temiClient } from './client.js';
import { registerZodTool } from '../../util/register-tool.js';

const Input = z.object({
  location: z.string().describe('Temi 地图上已保存的地点名,例如 "入口"、"生活仿真区"、"工位区"'),
});

const Output = z.object({
  ok: z.boolean(),
  mock: z.boolean(),
  message: z.string().optional(),
  error: z.string().optional(),
});

export function registerTemiNavigateTo(api: OpenClawPluginApi): void {
  registerZodTool(api, {
    name: 'feishu_classmate_temi_navigate_to',
    description:
      '控制 Temi 机器人移动到一个已保存的位置。当未连接真机(mockMode=true)时返回模拟成功。',
    inputSchema: Input,
    outputSchema: Output,
    async execute(input) {
      const cfg = getConfigFromApi(api);
      const res = await temiClient.post(
        cfg,
        '/goto',
        { location: input.location },
        { mockReturn: { ok: true, message: `(模拟)Temi 已导航到 ${input.location}` } },
      );
      return {
        ok: res.ok,
        mock: res.mock,
        message: (res.data as { message?: string } | undefined)?.message,
        error: res.error,
      };
    },
  });
}
