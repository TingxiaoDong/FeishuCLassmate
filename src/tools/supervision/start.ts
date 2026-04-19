/**
 * Supervision is a long-running, stateful interaction. We keep session state
 * in-memory on the plugin process (suitable for single-node deploy). For
 * multi-node, move this to a KV store.
 */

import type { OpenClawPluginApi } from 'openclaw/plugin-sdk';
import { z } from 'zod';
import { getConfigFromApi } from '../../config.js';
import { registerZodTool } from '../../util/register-tool.js';

interface SupervisionSession {
  session_id: string;
  student_open_id: string;
  goal: string;
  started_at: number;
  duration_ms: number;
  interval_ms: number;
  last_check_at: number;
  progress_notes: string[];
}

const SESSIONS = new Map<string, SupervisionSession>();

const StartInput = z.object({
  student_open_id: z.string(),
  goal: z.string().describe('学生说的目标,例如 "把 RLHF 技术路线跑通"'),
  duration_hours: z.number().min(0.25).max(8).default(4),
  interval_minutes: z.number().int().min(5).max(60).optional(),
});

const StartOutput = z.object({
  ok: z.boolean(),
  session_id: z.string().optional(),
  next_check_at_iso: z.string().optional(),
  error: z.string().optional(),
});

export function registerSupervisionStart(api: OpenClawPluginApi): void {
  registerZodTool(api, {
    name: 'feishu_classmate_supervision_start',
    description:
      '启动一次自我监督会话。每隔 interval_minutes 分钟,Agent 会通过飞书询问进度;' +
      '默认 10 分钟一次。返回 session_id,由调用方或 service 心跳驱动 tick。',
    inputSchema: StartInput,
    outputSchema: StartOutput,
    async execute(input) {
      const cfg = getConfigFromApi(api);
      if (input.duration_hours > cfg.supervision.maxDurationHours) {
        return {
          ok: false,
          error: `duration_hours 超过最大值 ${cfg.supervision.maxDurationHours}`,
        };
      }

      const interval = (input.interval_minutes ?? cfg.supervision.defaultIntervalMinutes) * 60_000;
      const sessionId = `sup_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 6)}`;

      const now = Date.now();
      SESSIONS.set(sessionId, {
        session_id: sessionId,
        student_open_id: input.student_open_id,
        goal: input.goal,
        started_at: now,
        duration_ms: input.duration_hours * 3_600_000,
        interval_ms: interval,
        last_check_at: now,
        progress_notes: [],
      });

      return {
        ok: true,
        session_id: sessionId,
        next_check_at_iso: new Date(now + interval).toISOString(),
      };
    },
  });
}

export function getSupervisionSessions(): SupervisionSession[] {
  return [...SESSIONS.values()];
}

export function getSupervisionSession(id: string): SupervisionSession | undefined {
  return SESSIONS.get(id);
}

export function recordSupervisionNote(id: string, note: string): void {
  const s = SESSIONS.get(id);
  if (!s) return;
  s.progress_notes.push(note);
  s.last_check_at = Date.now();
}

export function endSupervisionSession(id: string): SupervisionSession | undefined {
  const s = SESSIONS.get(id);
  SESSIONS.delete(id);
  return s;
}
