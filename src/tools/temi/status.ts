import type { OpenClawPluginApi } from 'openclaw/plugin-sdk';
import { z } from 'zod';
import { getConfigFromApi } from '../../config.js';
import { temiClient } from './client.js';
import { registerZodTool } from '../../util/register-tool.js';

const Output = z.object({
  ok: z.boolean(),
  mock: z.boolean(),
  connected: z.boolean(),
  battery: z.number().optional(),
  position: z.object({ x: z.number(), y: z.number() }).optional(),
  is_moving: z.boolean().optional(),
  error: z.string().optional(),
});

export function registerTemiStatus(api: OpenClawPluginApi): void {
  registerZodTool(api, {
    name: 'feishu_classmate_temi_status',
    description: '查询 Temi 当前连接状态、电量和位置。供 skill 在导览前做可用性判断。',
    inputSchema: z.object({}),
    outputSchema: Output,
    async execute() {
      const cfg = getConfigFromApi(api);
      const res = await temiClient.get(cfg, '/status', {
        mockReturn: { connected: false, battery: 0, position: { x: 0, y: 0 }, is_moving: false },
      });
      const data = (res.data ?? {}) as {
        connected?: boolean;
        battery?: number;
        position?: { x: number; y: number };
        is_moving?: boolean;
      };
      return {
        ok: res.ok,
        mock: res.mock,
        connected: data.connected ?? false,
        battery: data.battery,
        position: data.position,
        is_moving: data.is_moving,
        error: res.error,
      };
    },
  });
}
