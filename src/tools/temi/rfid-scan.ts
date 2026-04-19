import type { OpenClawPluginApi } from 'openclaw/plugin-sdk';
import { z } from 'zod';
import { getConfigFromApi } from '../../config.js';
import { temiClient } from './client.js';
import { registerZodTool } from '../../util/register-tool.js';

const Input = z.object({
  route: z
    .array(z.string())
    .optional()
    .describe('可选的巡检路径(地点名列表)。为空则由 sidecar 使用默认路径。'),
});

const RfidTag = z.object({
  tag_id: z.string(),
  location_estimate: z.string(),
  rssi: z.number(),
});

const Output = z.object({
  ok: z.boolean(),
  mock: z.boolean(),
  tags: z.array(RfidTag),
  error: z.string().optional(),
});

export function registerTemiRfidScan(api: OpenClawPluginApi): void {
  registerZodTool(api, {
    name: 'feishu_classmate_temi_rfid_scan_route',
    description:
      '驱动 Temi 沿指定路径扫描 RFID 标签,返回检测到的 tag 列表(id、估计位置、信号强度)。' +
      '用于资产巡查。mockMode 下返回模拟的 2-3 条数据。',
    inputSchema: Input,
    outputSchema: Output,
    async execute(input) {
      const cfg = getConfigFromApi(api);
      const res = await temiClient.post<{ tags: Array<{ tag_id: string; location_estimate: string; rssi: number }> }>(
        cfg,
        '/rfid-scan',
        { route: input.route ?? null },
        {
          timeoutMs: 60_000,
          mockReturn: {
            tags: [
              { tag_id: 'TAG-001A', location_estimate: '工位区-A3', rssi: -62 },
              { tag_id: 'TAG-002B', location_estimate: '生活仿真区', rssi: -71 },
              { tag_id: 'TAG-003C', location_estimate: '入口', rssi: -55 },
            ],
          },
        },
      );
      return {
        ok: res.ok,
        mock: res.mock,
        tags: res.data?.tags ?? [],
        error: res.error,
      };
    },
  });
}
