/**
 * Supervision ticker — once per minute, walks all active supervision sessions
 * and either pings the student for a progress update or closes out sessions
 * whose duration has elapsed.
 *
 * Session state lives in-process (see tools/supervision/start.ts). That is
 * intentional for a single-node deploy; for multi-node, persist to KV and
 * adapt this ticker to read from it.
 */

import type { OpenClawPluginApi } from 'openclaw/plugin-sdk';
import { getConfigFromApi } from '../config.js';
import { getFeishuClient } from '../util/feishu-api.js';
import { scheduleCron } from '../util/cron.js';
import {
  getSupervisionSessions,
  endSupervisionSession,
} from '../tools/supervision/index.js';

export function registerSupervisionTicker(api: OpenClawPluginApi): void {
  const run = async () => {
    const cfg = getConfigFromApi(api);
    const sessions = getSupervisionSessions();
    if (sessions.length === 0) return;

    const client = getFeishuClient(cfg);
    const now = Date.now();

    for (const s of sessions) {
      const elapsed = now - s.started_at;

      // Duration exceeded → finish & drop
      if (elapsed >= s.duration_ms) {
        const finalText =
          `✅ 监督会话结束(session_id=${s.session_id})\n` +
          `目标:${s.goal}\n` +
          `共记录 ${s.progress_notes.length} 次进度。辛苦了!`;
        const send = await client.sendText({
          receive_id: s.student_open_id,
          receive_id_type: 'open_id',
          text: finalText,
        });
        if (!send.ok) {
          api.logger?.warn?.(
            `[classmate/supervision-ticker] end-message to ${s.student_open_id} failed: ${send.error}`,
          );
        }
        endSupervisionSession(s.session_id);
        continue;
      }

      // Still active → check if it's time for the next progress ping
      if (now - s.last_check_at < s.interval_ms) continue;

      const prompt =
        `⏰ 监督 check-in(session_id=${s.session_id})\n` +
        `目标:${s.goal}\n` +
        `已过 ${Math.round(elapsed / 60_000)} 分钟。请回复当前进度 / 卡点 / 下一步;` +
        `我会记录下来。`;
      const send = await client.sendText({
        receive_id: s.student_open_id,
        receive_id_type: 'open_id',
        text: prompt,
      });
      if (!send.ok) {
        api.logger?.warn?.(
          `[classmate/supervision-ticker] ping to ${s.student_open_id} failed: ${send.error}`,
        );
        continue;
      }
      // Advance last_check_at so we don't re-ping next minute. The student's
      // reply handler (if wired) can override via recordSupervisionNote.
      s.last_check_at = now;
    }
  };

  api.registerService?.({
    id: 'classmate-supervision-ticker',
    async start(){
      scheduleCron('*/1 * * * *', run);
      api.logger?.info?.('[classmate/supervision-ticker] registered cron: */1 * * * *');
    },
  } as Parameters<NonNullable<OpenClawPluginApi['registerService']>>[0]);
}
