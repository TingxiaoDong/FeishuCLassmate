/**
 * feishu_classmate_chat_should_engage — decide whether the bot should proactively
 * chat with a given student. Declines when a supervision session is active or
 * when the last interaction was less than 2 hours ago.
 */

import type { OpenClawPluginApi } from 'openclaw/plugin-sdk';
import { z } from 'zod';
import { getSupervisionSessions } from '../supervision/start.js';
import { registerZodTool } from '../../util/register-tool.js';

const Input = z.object({
  student_open_id: z.string().min(1),
});

const Output = z.object({
  engage: z.boolean(),
  reason: z.string().optional(),
  last_interaction_at: z.string().optional(),
});

const COOLDOWN_MS = 2 * 3_600_000;

/** open_id -> last chat initiation timestamp (ms). Module-level, survives per process. */
const LAST_INTERACTION = new Map<string, number>();

export function registerChatShouldEngage(api: OpenClawPluginApi): void {
  registerZodTool(api, {
    name: 'feishu_classmate_chat_should_engage',
    description:
      '判断现在是否适合主动找这位学生闲聊。考虑:是否有进行中的 supervision session、距上次互动是否 > 2 小时。批准则把本次记录为一次互动。',
    inputSchema: Input,
    outputSchema: Output,
    async execute(input) {
      // Reject if any active supervision session belongs to this student.
      const active = getSupervisionSessions().find(
        (s) => s.student_open_id === input.student_open_id,
      );
      if (active) {
        return { engage: false, reason: 'supervision active' };
      }

      const now = Date.now();
      const last = LAST_INTERACTION.get(input.student_open_id);
      if (last !== undefined && now - last < COOLDOWN_MS) {
        return {
          engage: false,
          reason: 'cooldown: last interaction < 2h ago',
          last_interaction_at: new Date(last).toISOString(),
        };
      }

      // Approve and mark this call as an interaction.
      LAST_INTERACTION.set(input.student_open_id, now);
      return {
        engage: true,
        last_interaction_at: new Date(now).toISOString(),
      };
    },
  });
}

/** Test hook — lets services reset state between runs. */
export function clearChatInteractionCache(): void {
  LAST_INTERACTION.clear();
}
