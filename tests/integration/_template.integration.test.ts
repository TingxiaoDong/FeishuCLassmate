/**
 * Template for new E2E integration tests.
 *
 * Copy this file to `<feature>.integration.test.ts` and fill in the blanks.
 * Guidelines:
 *   - One `describe` per feature / tool chain.
 *   - Use `createFakeConfig` + `createFakeApi` from tests/helpers.
 *   - Use `createMockFeishuClient` + `vi.mock('.../feishu-api.js', ...)` when
 *     the tool writes to Bitable.
 *   - When the tool calls global `fetch`, use `vi.stubGlobal('fetch', ...)`
 *     in beforeEach and `vi.unstubAllGlobals()` in afterEach.
 *   - Reset any module-level state the tool owns (e.g. supervision sessions,
 *     chat throttle cache) in a `beforeEach` so parallel test files don't
 *     interfere.
 *   - Prefer asserting structural shape over exact strings — the goal is to
 *     catch schema drift, not lock in copy.
 */
import { describe, expect, it } from 'vitest';
import { createFakeConfig } from '../helpers/fake-config.js';
import { createFakeApi, type ToolDef } from '../helpers/fake-api.js';

describe.skip('integration: <feature>', () => {
  it('happy path: tool chain produces the expected shape', async () => {
    const config = createFakeConfig();
    const { api, tools } = createFakeApi({ config });

    // 1. Register your tool(s) here:
    //    registerMyTool(api as never);

    const tool = tools.get('feishu_classmate_my_tool') as ToolDef | undefined;
    expect(tool).toBeDefined();

    // 2. Invoke and assert.
    const result = (await tool!.execute({
      /* inputs */
    })) as Record<string, unknown>;
    expect(result.ok).toBe(true);
  });

  it('error path: bad input / failing dep surfaces as {ok:false}', async () => {
    // Stub a dependency to fail and assert graceful error reporting.
  });
});
