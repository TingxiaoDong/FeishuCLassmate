/**
 * E2E integration: Temi tool chain against the mock sidecar path.
 *
 * 1. `cfg.temi.mockMode = true`: every tool returns {ok:true, mock:true}
 *    without touching global fetch — the sidecar never has to be reachable.
 * 2. `cfg.temi.mockMode = false` + fetch rejected: navigate_to surfaces the
 *    error as {ok:false, error:...} instead of throwing.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { createFakeConfig } from '../helpers/fake-config.js';
import { createFakeApi, type ToolDef } from '../helpers/fake-api.js';
import { registerTemiTools } from '../../src/tools/temi/index.js';

/** Register every Temi tool against a single fake api and return a lookup map. */
function registerAll(mockMode: boolean) {
  const config = createFakeConfig({
    temi: { sidecarUrl: 'http://127.0.0.1:8091', mockMode },
  });
  const { api, tools } = createFakeApi({ config });
  registerTemiTools(api as never);
  return {
    tools,
    nav: tools.get('feishu_classmate_temi_navigate_to') as ToolDef,
    speak: tools.get('feishu_classmate_temi_speak') as ToolDef,
    stop: tools.get('feishu_classmate_temi_stop') as ToolDef,
    detect: tools.get('feishu_classmate_temi_detect_person') as ToolDef,
    rfid: tools.get('feishu_classmate_temi_rfid_scan_route') as ToolDef,
    focus: tools.get('feishu_classmate_temi_monitor_focus') as ToolDef,
    gesture: tools.get('feishu_classmate_temi_gesture') as ToolDef,
    status: tools.get('feishu_classmate_temi_status') as ToolDef,
  };
}

describe('integration: Temi tools with cfg.temi.mockMode = true', () => {
  it('every Temi tool returns {ok:true, mock:true}', async () => {
    const t = registerAll(true);

    const results = await Promise.all([
      t.nav.execute({ location: '入口' }),
      t.speak.execute({ text: '你好', voice: 'friendly' }),
      t.stop.execute({ immediate: false }),
      t.detect.execute({ timeout_ms: 1000 }),
      t.rfid.execute({}),
      t.focus.execute({ student_open_id: 'ou_stu', duration_s: 30 }),
      t.gesture.execute({ type: 'nod' }),
      t.status.execute({}),
    ]);

    for (const r of results) {
      const obj = r as Record<string, unknown>;
      expect(obj.ok).toBe(true);
      expect(obj.mock).toBe(true);
    }
  });
});

describe('integration: Temi tools with cfg.temi.mockMode = false and fetch rejected', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('navigate_to returns {ok:false, mock:false, error} when fetch throws', async () => {
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockRejectedValue(
      new Error('ECONNREFUSED 127.0.0.1:8091'),
    );
    const t = registerAll(false);

    const res = (await t.nav.execute({ location: '工位区' })) as Record<string, unknown>;
    expect(res.ok).toBe(false);
    expect(res.mock).toBe(false);
    expect(typeof res.error).toBe('string');
    expect((res.error as string).length).toBeGreaterThan(0);
  });
});
