/**
 * E2E integration: full supervision session lifecycle.
 *
 *   start  → tick(in-progress)  → tick(done)  → summarize → tick(invalid_id)
 *
 * Exercises the real in-memory SESSIONS map in src/tools/supervision/start.ts,
 * confirming tick and summarize see the same state the agent just wrote.
 */
import { describe, expect, it } from 'vitest';
import { createFakeConfig } from '../helpers/fake-config.js';
import { createFakeApi, type ToolDef } from '../helpers/fake-api.js';
import {
  registerSupervisionStart,
  endSupervisionSession,
  getSupervisionSessions,
} from '../../src/tools/supervision/start.js';
import { registerSupervisionTick } from '../../src/tools/supervision/tick.js';
import { registerSupervisionSummarize } from '../../src/tools/supervision/summarize.js';

/** Register all three supervision tools against a shared fake api. */
function setupSupervisionTools() {
  const config = createFakeConfig();
  const { api, tools } = createFakeApi({ config });
  registerSupervisionStart(api as never);
  registerSupervisionTick(api as never);
  registerSupervisionSummarize(api as never);
  return {
    start: tools.get('feishu_classmate_supervision_start') as ToolDef,
    tick: tools.get('feishu_classmate_supervision_tick') as ToolDef,
    summarize: tools.get('feishu_classmate_supervision_summarize') as ToolDef,
  };
}

/** Clear any stale sessions left by other test files (module-level state). */
function clearAllSessions() {
  for (const s of getSupervisionSessions()) {
    endSupervisionSession(s.session_id);
  }
}

describe('integration: supervision lifecycle', () => {
  it('start → tick(in-progress) → tick(done) → summarize', async () => {
    clearAllSessions();
    const { start, tick, summarize } = setupSupervisionTools();

    // 1. start
    const goal = '把 RLHF 技术路线跑通';
    const startRes = (await start.execute({
      student_open_id: 'ou_student_lifecycle',
      goal,
      duration_hours: 2,
    })) as { ok: boolean; session_id?: string };
    expect(startRes.ok).toBe(true);
    expect(typeof startRes.session_id).toBe('string');
    const sessionId = startRes.session_id!;

    // 2. in-progress tick
    const tick1 = (await tick.execute({
      session_id: sessionId,
      student_reply: '50%, 进行中',
    })) as { ok: boolean; next_action?: string; classification?: string };
    expect(tick1.ok).toBe(true);
    expect(tick1.next_action).toBe('poll');
    expect(tick1.classification).toBe('进行中');

    // 3. done tick
    const tick2 = (await tick.execute({
      session_id: sessionId,
      student_reply: '搞定了',
    })) as { ok: boolean; next_action?: string; classification?: string };
    expect(tick2.ok).toBe(true);
    expect(tick2.classification).toBe('已完成');
    expect(tick2.next_action).toBe('finish');

    // 4. summarize
    const sumRes = (await summarize.execute({ session_id: sessionId })) as {
      ok: boolean;
      summary_markdown: string;
      duration_actual_ms: number;
      note_count: number;
    };
    expect(sumRes.ok).toBe(true);
    expect(sumRes.note_count).toBe(2);
    expect(sumRes.summary_markdown).toContain(goal);
    // Duration formatter renders `x 分钟` / `x 小时 y 分钟`; assert either shape.
    expect(sumRes.summary_markdown).toMatch(/分钟|小时/);
    // "打卡次数" is our shorthand for notes count in the summary template.
    expect(sumRes.summary_markdown).toContain('打卡次数');
    // Progress notes should be embedded in the markdown.
    expect(sumRes.summary_markdown).toContain('进行中');
    expect(sumRes.summary_markdown).toContain('已完成');
  });

  it('tick on invalid session_id returns {ok:false}', async () => {
    clearAllSessions();
    const { tick } = setupSupervisionTools();

    const res = (await tick.execute({
      session_id: 'sup_does_not_exist_xyz',
      student_reply: 'hi',
    })) as { ok: boolean; error?: string };
    expect(res.ok).toBe(false);
    expect(typeof res.error).toBe('string');
  });

  it('tick classifies a stuck reply and suggests intervene', async () => {
    clearAllSessions();
    const { start, tick } = setupSupervisionTools();

    const startRes = (await start.execute({
      student_open_id: 'ou_student_stuck',
      goal: '写评估脚本',
      duration_hours: 1,
    })) as { ok: boolean; session_id?: string };

    const res = (await tick.execute({
      session_id: startRes.session_id!,
      student_reply: '卡住了,脚本报错',
    })) as { ok: boolean; next_action?: string; classification?: string };
    expect(res.ok).toBe(true);
    expect(res.classification).toBe('卡住');
    expect(res.next_action).toBe('intervene');
  });

  it('summarize on invalid session_id returns {ok:false} with empty markdown', async () => {
    clearAllSessions();
    const { summarize } = setupSupervisionTools();

    const res = (await summarize.execute({ session_id: 'sup_missing_id' })) as {
      ok: boolean;
      summary_markdown: string;
      note_count: number;
    };
    expect(res.ok).toBe(false);
    expect(res.summary_markdown).toBe('');
    expect(res.note_count).toBe(0);
  });
});
