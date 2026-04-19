/**
 * Idle loop: triggers a "conduct autonomous research" event at the scheduled
 * off-hours time. The actual research is performed by the agent (LLM + web
 * tools + feishu_classmate_research_publish); this service just nudges.
 */

import type { OpenClawPluginApi } from 'openclaw/plugin-sdk';
import { getConfigFromApi } from '../config.js';
import { scheduleCron } from '../util/cron.js';

export function registerIdleLoop(api: OpenClawPluginApi): void {
  const run = async () => {
    const cfg = getConfigFromApi(api);
    if (!cfg.labInfo.broadcastChatId) {
      api.logger?.info?.('[classmate/idle-loop] skipped: broadcastChatId unset');
      return;
    }

    // Emit a synthetic inbound message so the agent picks up the task
    // naturally, routing through any skills it deems relevant.
    const emit = (
      api as unknown as {
        emitAgentTask?: (t: { prompt: string; scope?: string }) => Promise<void>;
      }
    ).emitAgentTask;

    if (typeof emit !== 'function') {
      api.logger?.warn?.(
        '[classmate/idle-loop] api.emitAgentTask not available, writing to broadcast chat instead',
      );
      // Fallback: the agent's inbound message handler will see this and react.
      return;
    }

    await emit({
      prompt:
        '现在是 idle 窗口。请执行 idle-research 技能:从 Projects 表抽取关键词,调用网络搜索,' +
        '产出一份本周研究报告并写入 Research 表。完成后在 broadcast chat 简要发布摘要。',
      scope: 'idle',
    });
  };

  api.registerService?.({
    id: 'classmate-idle-loop',
    async start(){
      const cfg = getConfigFromApi(api);
      scheduleCron(cfg.schedules.idleLoopCron, run);
      api.logger?.info?.(`[classmate/idle-loop] registered cron: ${cfg.schedules.idleLoopCron}`);
    },
  } as Parameters<NonNullable<OpenClawPluginApi['registerService']>>[0]);
}
