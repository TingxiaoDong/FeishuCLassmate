/**
 * feishu_classmate_supervision_tick — one heartbeat of a supervision session.
 * Called periodically (or after a student replies) to decide the next action.
 */

import type { OpenClawPluginApi } from 'openclaw/plugin-sdk';
import { z } from 'zod';
import { getSupervisionSession, recordSupervisionNote } from './start.js';
import { registerZodTool } from '../../util/register-tool.js';

const Input = z.object({
  session_id: z.string().min(1),
  student_reply: z.string().optional(),
});

const Output = z.object({
  ok: z.boolean(),
  next_action: z.enum(['poll', 'intervene', 'finish']).optional(),
  classification: z.enum(['进行中', '卡住', '已完成']).optional(),
  message: z.string().optional(),
  error: z.string().optional(),
});

const REMINDER_TEMPLATES = [
  '10 分钟到了,现在进度怎么样?一句话告诉我就行~',
  '叮——阶段性打卡时间到,当前卡在哪一步了?',
  '我来催个进度,你现在大概完成多少?需要我帮忙查点什么吗?',
];

export function registerSupervisionTick(api: OpenClawPluginApi): void {
  registerZodTool(api, {
    name: 'feishu_classmate_supervision_tick',
    description:
      '监督会话的一次心跳。如果提供 student_reply 就解析进度;否则返回下一条提醒文案。到期自动返回 finish。',
    inputSchema: Input,
    outputSchema: Output,
    async execute(input) {
      const session = getSupervisionSession(input.session_id);
      if (!session) {
        return { ok: false, error: 'session not found' };
      }

      const now = Date.now();
      if (session.started_at + session.duration_ms < now) {
        return { ok: true, next_action: 'finish' };
      }

      if (input.student_reply !== undefined) {
        const reply = input.student_reply.trim();
        const classification = classifyReply(reply);
        const note = `[${new Date(now).toISOString()}] (${classification}) ${reply}`;
        recordSupervisionNote(input.session_id, note);

        if (classification === '已完成') {
          return {
            ok: true,
            next_action: 'finish',
            classification,
            message: '太好了,辛苦!我一会儿把这次的小结写进日常记录。',
          };
        }
        if (classification === '卡住') {
          return {
            ok: true,
            next_action: 'intervene',
            classification,
            message: '听起来卡住了,我来帮你拆一下下一步吧——具体是哪个环节过不去?',
          };
        }
        return {
          ok: true,
          next_action: 'poll',
          classification,
          message: '好,继续~',
        };
      }

      // No reply yet — just emit a friendly reminder for the scheduler to send.
      const template = REMINDER_TEMPLATES[Math.floor(Math.random() * REMINDER_TEMPLATES.length)];
      return {
        ok: true,
        next_action: 'poll',
        message: template,
      };
    },
  });
}

/** Heuristic classifier for a student's short progress reply. */
function classifyReply(reply: string): '进行中' | '卡住' | '已完成' {
  if (/已?完成|搞定|done|finish|结束/i.test(reply)) return '已完成';
  if (/卡住|卡在|不会|搞不定|stuck|blocked|报错/i.test(reply)) return '卡住';
  // Progress percentages count as "in progress" even if 100% is mentioned in a
  // hedging way; explicit "done" wording above already claimed those cases.
  const pct = reply.match(/(\d{1,3})\s*%/);
  if (pct) {
    const n = Number(pct[1]);
    if (!Number.isNaN(n) && n >= 100) return '已完成';
  }
  return '进行中';
}
