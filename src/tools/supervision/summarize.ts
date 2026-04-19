/**
 * feishu_classmate_supervision_summarize — wrap up a supervision session and
 * emit a markdown summary for the caller to post to 【日常记录】.
 */

import type { OpenClawPluginApi } from 'openclaw/plugin-sdk';
import { z } from 'zod';
import { getSupervisionSession, endSupervisionSession } from './start.js';
import { registerZodTool } from '../../util/register-tool.js';

const Input = z.object({
  session_id: z.string().min(1),
});

const Output = z.object({
  ok: z.boolean(),
  summary_markdown: z.string(),
  duration_actual_ms: z.number(),
  note_count: z.number(),
  error: z.string().optional(),
});

export function registerSupervisionSummarize(api: OpenClawPluginApi): void {
  registerZodTool(api, {
    name: 'feishu_classmate_supervision_summarize',
    description:
      '结束并汇总一次监督会话,返回 markdown 小结(目标 / 实际时长 / 笔记条数 / 每条时间戳)。不写入任何地方,调用方负责投递到【日常记录】。',
    inputSchema: Input,
    outputSchema: Output,
    async execute(input) {
      const session = getSupervisionSession(input.session_id);
      if (!session) {
        return {
          ok: false,
          summary_markdown: '',
          duration_actual_ms: 0,
          note_count: 0,
          error: 'session not found',
        };
      }

      const now = Date.now();
      const durationActual = now - session.started_at;
      const noteCount = session.progress_notes.length;

      const lines: string[] = [];
      lines.push(`## 监督小结 · ${session.session_id}`);
      lines.push('');
      lines.push(`- **目标**: ${session.goal}`);
      lines.push(`- **计划时长**: ${formatMs(session.duration_ms)}`);
      lines.push(`- **实际时长**: ${formatMs(durationActual)}`);
      lines.push(`- **打卡次数**: ${noteCount}`);
      if (noteCount > 0) {
        lines.push('');
        lines.push('### 进度记录');
        for (const note of session.progress_notes) {
          lines.push(`- ${note}`);
        }
      }

      // End the session after summary is built.
      endSupervisionSession(input.session_id);

      return {
        ok: true,
        summary_markdown: lines.join('\n'),
        duration_actual_ms: durationActual,
        note_count: noteCount,
      };
    },
  });
}

function formatMs(ms: number): string {
  if (ms < 0) return '0 分钟';
  const totalMinutes = Math.round(ms / 60_000);
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;
  if (hours === 0) return `${minutes} 分钟`;
  if (minutes === 0) return `${hours} 小时`;
  return `${hours} 小时 ${minutes} 分钟`;
}
