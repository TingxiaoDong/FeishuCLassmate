/**
 * Project management scheduler: triggers periodic manage-project skill tasks
 * - Daily progress check at 12:00
 * - Weekly report generation at 18:00 every Sunday
 */

import type { OpenClawPluginApi } from 'openclaw/plugin-sdk';
import { getConfigFromApi } from '../config.js';
import { scheduleCron } from '../util/cron.js';

export function registerProjectScheduler(api: OpenClawPluginApi): void {
  // Daily progress check task
  const runProgressCheck = async () => {
    const cfg = getConfigFromApi(api);
    if (!cfg.labInfo.broadcastChatId) {
      api.logger?.info?.('[classmate/project-scheduler] skipped progress check: broadcastChatId unset');
      return;
    }

    const emit = (
      api as unknown as {
        emitAgentTask?: (t: { prompt: string; scope?: string }) => Promise<void>;
      }
    ).emitAgentTask;

    if (typeof emit !== 'function') {
      api.logger?.warn?.('[classmate/project-scheduler] api.emitAgentTask not available');
      return;
    }

    await emit({
      prompt: '请执行manage-project技能，完成今日所有项目的进度检查，标记逾期节点并给对应负责人发送提醒消息。',
      scope: 'scheduled',
    });
  };

  // Weekly report generation task
  const runWeeklyReport = async () => {
    const cfg = getConfigFromApi(api);
    if (!cfg.labInfo.broadcastChatId) {
      api.logger?.info?.('[classmate/project-scheduler] skipped weekly report: broadcastChatId unset');
      return;
    }

    const emit = (
      api as unknown as {
        emitAgentTask?: (t: { prompt: string; scope?: string }) => Promise<void>;
      }
    ).emitAgentTask;

    if (typeof emit !== 'function') {
      api.logger?.warn?.('[classmate/project-scheduler] api.emitAgentTask not available');
      return;
    }

    await emit({
      prompt: '请执行manage-project技能，生成本周的项目进度周报，写入Lab知识库并将报告链接发送到广播群。',
      scope: 'scheduled',
    });
  };

  api.registerService?.({
    id: 'classmate-project-scheduler',
    async start(){
      const cfg = getConfigFromApi(api);
      
      // Register daily progress check cron
      scheduleCron(cfg.schedules.projectProgressCheckCron, runProgressCheck);
      api.logger?.info?.(`[classmate/project-scheduler] registered progress check cron: ${cfg.schedules.projectProgressCheckCron}`);
      
      // Register weekly report cron
      scheduleCron(cfg.schedules.weeklyReportCron, runWeeklyReport);
      api.logger?.info?.(`[classmate/project-scheduler] registered weekly report cron: ${cfg.schedules.weeklyReportCron}`);
    },
  } as Parameters<NonNullable<OpenClawPluginApi['registerService']>>[0]);
}
