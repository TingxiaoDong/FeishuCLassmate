/**
 * /classmate — administrative / status commands.
 *
 * Subcommands:
 *   status         show plugin health, bitable readiness, temi connectivity
 *   setup-bitable  first-run table creation (idempotent)
 *   rebuild-schema alias of setup-bitable
 */

import type { OpenClawPluginApi } from 'openclaw/plugin-sdk';
import { getConfigFromApi } from '../config.js';
import { ensureBitableSchema, persistSetup } from '../bitable/setup.js';
import { temiClient } from '../tools/temi/client.js';

export function registerClassmateCommand(api: OpenClawPluginApi): void {
  api.registerCli?.(
    (ctx: { program: { command: (n: string) => unknown } }) => {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const program = ctx.program as any;

      const root = program.command('classmate').description('飞书同学控制命令');

      root
        .command('status')
        .description('显示插件当前健康状态')
        .action(async () => {
          const cfg = getConfigFromApi(api);
          const temiStatus = await temiClient.get(cfg, '/status', {
            mockReturn: { connected: false },
          });
          const data = (temiStatus.data ?? {}) as { connected?: boolean; battery?: number };

          // eslint-disable-next-line no-console
          console.log(
            JSON.stringify(
              {
                feishu: {
                  appId: cfg.feishu.appId
                    ? `${cfg.feishu.appId.slice(0, 6)}...`
                    : '(not set)',
                  domain: cfg.feishu.domain,
                },
                bitable: {
                  appToken: cfg.bitable.appToken
                    ? `${cfg.bitable.appToken.slice(0, 6)}...`
                    : '(not set)',
                  tables: cfg.bitable.tableIds ?? {},
                },
                temi: {
                  sidecarUrl: cfg.temi.sidecarUrl,
                  mockMode: cfg.temi.mockMode,
                  connected: temiStatus.ok ? (data.connected ?? false) : false,
                  battery: data.battery ?? null,
                  error: temiStatus.error,
                },
                labInfo: {
                  name: cfg.labInfo.name,
                  supervisor: cfg.labInfo.supervisorName,
                  broadcastChatId: cfg.labInfo.broadcastChatId ?? '(not set)',
                },
                schedules: cfg.schedules,
              },
              null,
              2,
            ),
          );
        });

      root
        .command('setup-bitable')
        .alias('rebuild-schema')
        .description('幂等创建 Projects / Gantt / Equipment / Research 四张多维表')
        .action(async () => {
          // eslint-disable-next-line no-console
          console.log('🔧 正在创建多维表 schema...');
          try {
            const result = await ensureBitableSchema(api);
            await persistSetup(api, result);
            // eslint-disable-next-line no-console
            console.log('✅ 完成');
            // eslint-disable-next-line no-console
            console.log(`   app_token  = ${result.appToken}`);
            for (const [k, v] of Object.entries(result.tableIds)) {
              // eslint-disable-next-line no-console
              console.log(`   ${k.padEnd(10)} = ${v}`);
            }
            if (result.warnings.length) {
              // eslint-disable-next-line no-console
              console.log('⚠️  警告:');
              result.warnings.forEach((w) => console.log(`   - ${w}`));
            }
          } catch (err) {
            // eslint-disable-next-line no-console
            console.error('❌ 失败:', err);
            process.exitCode = 1;
          }
        });
    },
    { commands: ['classmate'] },
  );
}
