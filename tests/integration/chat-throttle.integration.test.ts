/**
 * E2E integration: chat throttle / should-engage.
 *
 * Exercises the real module-level LAST_INTERACTION map in
 * src/tools/chat/should-engage.ts and its interaction with the supervision
 * session store from src/tools/supervision/start.ts. Per-student isolation
 * + supervision-active gating are the critical behaviors.
 */
import { beforeEach, describe, expect, it } from 'vitest';
import { createFakeConfig } from '../helpers/fake-config.js';
import { createFakeApi, type ToolDef } from '../helpers/fake-api.js';
import {
  registerChatShouldEngage,
  clearChatInteractionCache,
} from '../../src/tools/chat/should-engage.js';
import {
  registerSupervisionStart,
  endSupervisionSession,
  getSupervisionSessions,
} from '../../src/tools/supervision/start.js';

function setup() {
  const config = createFakeConfig();
  const { api, tools } = createFakeApi({ config });
  registerChatShouldEngage(api as never);
  registerSupervisionStart(api as never);
  return {
    shouldEngage: tools.get('feishu_classmate_chat_should_engage') as ToolDef,
    supervisionStart: tools.get('feishu_classmate_supervision_start') as ToolDef,
  };
}

/** Clear both caches so tests in this file don't bleed into each other. */
function clearCaches() {
  clearChatInteractionCache();
  for (const s of getSupervisionSessions()) {
    endSupervisionSession(s.session_id);
  }
}

describe('integration: chat throttle', () => {
  beforeEach(() => {
    clearCaches();
  });

  it('student_A: first call engages; immediate second call is throttled', async () => {
    const { shouldEngage } = setup();

    const first = (await shouldEngage.execute({ student_open_id: 'ou_student_A' })) as {
      engage: boolean;
      last_interaction_at?: string;
    };
    expect(first.engage).toBe(true);
    expect(typeof first.last_interaction_at).toBe('string');

    const second = (await shouldEngage.execute({ student_open_id: 'ou_student_A' })) as {
      engage: boolean;
      reason?: string;
    };
    expect(second.engage).toBe(false);
    // Reason should mention the cooldown / recency check.
    expect(typeof second.reason).toBe('string');
    expect(second.reason!.toLowerCase()).toMatch(/cooldown|recent|interaction/);
  });

  it('different students have independent throttle state', async () => {
    const { shouldEngage } = setup();

    const a = (await shouldEngage.execute({ student_open_id: 'ou_student_A' })) as {
      engage: boolean;
    };
    expect(a.engage).toBe(true);

    // student_B is a different key — should still engage even though A just did.
    const b = (await shouldEngage.execute({ student_open_id: 'ou_student_B' })) as {
      engage: boolean;
    };
    expect(b.engage).toBe(true);
  });

  it('refuses to engage with a student who has an active supervision session', async () => {
    const { shouldEngage, supervisionStart } = setup();

    const startRes = (await supervisionStart.execute({
      student_open_id: 'ou_student_C',
      goal: '调通环境',
      duration_hours: 1,
    })) as { ok: boolean; session_id?: string };
    expect(startRes.ok).toBe(true);

    const res = (await shouldEngage.execute({ student_open_id: 'ou_student_C' })) as {
      engage: boolean;
      reason?: string;
    };
    expect(res.engage).toBe(false);
    expect(typeof res.reason).toBe('string');
    expect(res.reason!.toLowerCase()).toContain('supervision');
  });
});
