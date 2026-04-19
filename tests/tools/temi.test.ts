/**
 * Tests for Temi tools:
 *   - All tools in mockMode=true return {ok:true, mock:true}
 *   - feishu_classmate_temi_navigate_to with mockMode=false and failing fetch → ok:false
 *
 * Temi tools communicate with a Python sidecar via global fetch.
 * No FeishuClient calls are made, so no feishu-api mock is needed.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { createFakeConfig } from '../helpers/fake-config.js';
import { createFakeApi, type ToolDef } from '../helpers/fake-api.js';
import { registerTemiNavigateTo } from '../../src/tools/temi/navigate-to.js';
import { registerTemiSpeak } from '../../src/tools/temi/speak.js';
import { registerTemiStop } from '../../src/tools/temi/stop.js';
import { registerTemiDetectPerson } from '../../src/tools/temi/detect-person.js';
import { registerTemiStatus } from '../../src/tools/temi/status.js';

// ---------------------------------------------------------------------------
// Mock mode tests (mockMode=true — default in fake config)
// ---------------------------------------------------------------------------

describe('Temi tools in mock mode', () => {
  const mockConfig = { temi: { sidecarUrl: 'http://127.0.0.1:8091', mockMode: true } };

  it('feishu_classmate_temi_navigate_to returns ok=true mock=true', async () => {
    const config = createFakeConfig(mockConfig);
    const { api, tools } = createFakeApi({ config });
    registerTemiNavigateTo(api as never);
    const tool = tools.get('feishu_classmate_temi_navigate_to') as ToolDef;

    const result = await tool.execute({ location: '入口' }) as Record<string, unknown>;
    expect(result.ok).toBe(true);
    expect(result.mock).toBe(true);
  });

  it('feishu_classmate_temi_speak returns ok=true mock=true', async () => {
    const config = createFakeConfig(mockConfig);
    const { api, tools } = createFakeApi({ config });
    registerTemiSpeak(api as never);
    const tool = tools.get('feishu_classmate_temi_speak') as ToolDef;

    const result = await tool.execute({ text: '你好，同学!', voice: 'friendly' }) as Record<string, unknown>;
    expect(result.ok).toBe(true);
    expect(result.mock).toBe(true);
  });

  it('feishu_classmate_temi_stop returns ok=true mock=true', async () => {
    const config = createFakeConfig(mockConfig);
    const { api, tools } = createFakeApi({ config });
    registerTemiStop(api as never);
    const tool = tools.get('feishu_classmate_temi_stop') as ToolDef;

    const result = await tool.execute({ immediate: false }) as Record<string, unknown>;
    expect(result.ok).toBe(true);
    expect(result.mock).toBe(true);
  });

  it('feishu_classmate_temi_detect_person returns ok=true mock=true and open_id=null', async () => {
    const config = createFakeConfig(mockConfig);
    const { api, tools } = createFakeApi({ config });
    registerTemiDetectPerson(api as never);
    const tool = tools.get('feishu_classmate_temi_detect_person') as ToolDef;

    const result = await tool.execute({ timeout_ms: 3000 }) as Record<string, unknown>;
    expect(result.ok).toBe(true);
    expect(result.mock).toBe(true);
    expect(result.open_id).toBeNull();
  });

  it('feishu_classmate_temi_status returns ok=true mock=true', async () => {
    const config = createFakeConfig(mockConfig);
    const { api, tools } = createFakeApi({ config });
    registerTemiStatus(api as never);
    const tool = tools.get('feishu_classmate_temi_status') as ToolDef;

    const result = await tool.execute({}) as Record<string, unknown>;
    expect(result.ok).toBe(true);
    expect(result.mock).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// feishu_classmate_temi_navigate_to with mockMode=false and failing fetch
// ---------------------------------------------------------------------------

describe('feishu_classmate_temi_navigate_to with mockMode=false', () => {
  const liveConfig = { temi: { sidecarUrl: 'http://127.0.0.1:8091', mockMode: false } };

  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('returns ok=false mock=false when fetch throws a network error', async () => {
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockRejectedValue(new Error('ECONNREFUSED'));

    const config = createFakeConfig(liveConfig);
    const { api, tools } = createFakeApi({ config });
    registerTemiNavigateTo(api as never);
    const tool = tools.get('feishu_classmate_temi_navigate_to') as ToolDef;

    const result = await tool.execute({ location: '工位区' }) as Record<string, unknown>;
    expect(result.ok).toBe(false);
    expect(result.mock).toBe(false);
    expect(typeof result.error).toBe('string');
  });

  it('returns ok=false mock=false when fetch returns a non-ok HTTP status', async () => {
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: false,
      status: 503,
      text: async () => 'Service Unavailable',
    });

    const config = createFakeConfig(liveConfig);
    const { api, tools } = createFakeApi({ config });
    registerTemiNavigateTo(api as never);
    const tool = tools.get('feishu_classmate_temi_navigate_to') as ToolDef;

    const result = await tool.execute({ location: '生活仿真区' }) as Record<string, unknown>;
    expect(result.ok).toBe(false);
    expect(result.mock).toBe(false);
    expect((result.error as string)).toContain('503');
  });

  it('returns ok=true mock=false when fetch succeeds', async () => {
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ message: 'navigating' }),
    });

    const config = createFakeConfig(liveConfig);
    const { api, tools } = createFakeApi({ config });
    registerTemiNavigateTo(api as never);
    const tool = tools.get('feishu_classmate_temi_navigate_to') as ToolDef;

    const result = await tool.execute({ location: '入口' }) as Record<string, unknown>;
    expect(result.ok).toBe(true);
    expect(result.mock).toBe(false);
  });
});
