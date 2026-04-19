/**
 * OpenClaw plugin entry point — feishu-classmate
 *
 * Registers all tools, services, and commands; wires startup hooks.
 */

import type { OpenClawPluginApi } from 'openclaw/plugin-sdk';
import { emptyPluginConfigSchema } from 'openclaw/plugin-sdk';
import { registerAllTools } from './src/tools/index.js';
import { registerAllServices } from './src/services/index.js';
import { registerAllCommands } from './src/commands/index.js';
import { ensureBitableSchema, persistSetup } from './src/bitable/setup.js';
import { getConfigFromApi } from './src/config.js';
import { getFeishuClient } from './src/util/feishu-api.js';

// Re-export so external consumers can trigger setup programmatically.
export { ensureBitableSchema, persistSetup } from './src/bitable/setup.js';

const PLUGIN_ID = 'feishu-classmate';

const plugin = {
  id: PLUGIN_ID,
  name: '飞书同学',
  description: 'Feishu-based lab-mate: project tracking, equipment booking, student supervision, idle research, and casual conversation.',
  configSchema: emptyPluginConfigSchema(),

  register(api: OpenClawPluginApi): void {
    api.logger?.info?.(`[${PLUGIN_ID}] starting up…`);

    try {
      registerAllTools(api);
    } catch (err) {
      api.logger?.error?.(`[${PLUGIN_ID}] registerAllTools threw: ${err instanceof Error ? err.stack ?? err.message : String(err)}`);
      throw err;
    }
    try {
      registerAllServices(api);
    } catch (err) {
      api.logger?.error?.(`[${PLUGIN_ID}] registerAllServices threw: ${err instanceof Error ? err.stack ?? err.message : String(err)}`);
      throw err;
    }
    try {
      registerAllCommands(api);
    } catch (err) {
      api.logger?.error?.(`[${PLUGIN_ID}] registerAllCommands threw: ${err instanceof Error ? err.stack ?? err.message : String(err)}`);
      throw err;
    }

    // Concise one-line log per feishu_classmate_ tool call +
    // Phase-1 self-evolution telemetry: best-effort write to the ToolTrace
    // bitable table. Never blocks tool return; swallows any write failure.
    api.on('after_tool_call', (event, ctx) => {
      if (!event.toolName.startsWith('feishu_classmate_')) return;
      const sid = ctx.sessionKey ?? '-';
      const ms = event.durationMs ?? 0;
      if (event.error) {
        api.logger?.error?.(`[${PLUGIN_ID}] tool fail: ${event.toolName} session=${sid} error=${event.error} (${ms}ms)`);
      } else {
        api.logger?.info?.(`[${PLUGIN_ID}] tool done: ${event.toolName} session=${sid} ok (${ms}ms)`);
      }

      // --- ToolTrace telemetry (fire-and-forget) ---------------------------
      // Captured synchronously so the started_at timestamp aligns with
      // (now - durationMs). All downstream I/O is async in an IIFE so the
      // hook returns immediately.
      const startedAtMs = Date.now() - ms;
      const toolName = event.toolName;
      const errorStr = event.error ? String(event.error) : '';
      const ok = !event.error;
      let paramsJson = '';
      try {
        paramsJson = JSON.stringify(event.params ?? {});
        // Cap to ~8KB so we don't overflow a Text cell on pathological payloads.
        if (paramsJson.length > 8000) paramsJson = paramsJson.slice(0, 8000) + '…<truncated>';
      } catch {
        paramsJson = '<unserializable>';
      }
      const traceId = `tr_${startedAtMs}_${Math.random().toString(36).slice(2, 8)}`;
      const runId = (ctx as unknown as { runId?: string }).runId ?? '';
      const sessionKey = ctx.sessionKey ?? runId ?? '';
      const callerOpenId = (ctx as unknown as { userOpenId?: string; openId?: string })
        .userOpenId ?? (ctx as unknown as { openId?: string }).openId ?? '';

      (async () => {
        try {
          const cfg = getConfigFromApi(api);
          const appToken = cfg.bitable.appToken;
          const traceTableId = cfg.bitable.tableIds?.tool_trace;
          // If bitable isn't set up yet, just skip — don't throw.
          if (!appToken || !traceTableId) return;
          const client = getFeishuClient(cfg);
          const fields: Record<string, unknown> = {
            trace_id: traceId,
            tool_name: toolName,
            session_key: sessionKey,
            params_json: paramsJson,
            ok,
            error: errorStr,
            duration_ms: ms,
            started_at: startedAtMs,
          };
          if (callerOpenId) {
            fields.caller_open_id = [{ id: callerOpenId }];
          }
          const res = await client.createRecord(appToken, traceTableId, fields);
          if (!res.ok) {
            api.logger?.debug?.(
              `[${PLUGIN_ID}] tool_trace write skipped: ${res.error} (code=${res.code ?? '?'})`,
            );
          }
        } catch (err) {
          // Telemetry must never surface to the caller.
          api.logger?.debug?.(
            `[${PLUGIN_ID}] tool_trace write threw: ${err instanceof Error ? err.message : String(err)}`,
          );
        }
      })();
    });

    // Best-effort Bitable schema setup at startup.
    // Plugin still loads even if Feishu credentials are absent.
    (async () => {
      try {
        const result = await ensureBitableSchema(api);
        await persistSetup(api, result);
        if (result.created) {
          api.logger?.info?.(`[${PLUGIN_ID}] bitable app created: ${result.appToken}`);
        }
        if (result.warnings.length > 0) {
          for (const w of result.warnings) {
            api.logger?.warn?.(`[${PLUGIN_ID}] bitable setup warning: ${w}`);
          }
        }
      } catch (err: unknown) {
        // Credentials not configured yet — expected during first install.
        const msg = err instanceof Error ? err.message : String(err);
        api.logger?.warn?.(
          `[${PLUGIN_ID}] bitable setup skipped (Feishu not configured): ${msg}`,
        );
      }
    })();

    api.logger?.info?.(`[${PLUGIN_ID}] registered.`);
  },
};

export default plugin;
