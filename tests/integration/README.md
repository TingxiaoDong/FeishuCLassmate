# Integration tests

End-to-end tool-chain tests for `feishu-classmate`. Unit tests in `tests/tools/`
cover a single function with heavy mocking; integration tests here exercise the
full **agent → tool registration → tool execute → shared in-memory state** path
against a fake OpenClaw `api` plus a mock Feishu SDK. These catch bugs unit
tests miss, e.g. schema-field drift between `src/bitable/schema.ts` and
`src/tools/data-layout.ts`, or cross-tool state leaks (supervision ↔ chat).

## How to run

```bash
pnpm test tests/integration/
```

To run a single integration file:

```bash
pnpm test tests/integration/supervision-lifecycle.integration.test.ts
```

The full `pnpm test` suite includes both unit and integration tests and must
pass in CI.

## What each test covers

| File | Covers |
| --- | --- |
| `data-layout.integration.test.ts` | `feishu_classmate_data_layout` returns `app_token` + `tables` map with every entry in `ALL_TABLES`. Pins SingleSelect option sets (`projects.visibility`, `equipment.state`) so schema renames can't silently ship. |
| `supervision-lifecycle.integration.test.ts` | Full `start → tick(in-progress) → tick(done) → summarize` flow, plus the invalid-session-id error path. Exercises the real module-level `SESSIONS` map. |
| `chat-throttle.integration.test.ts` | `should_engage` cooldown per student, per-student isolation, and supervision-session gating. Exercises `LAST_INTERACTION` + `SESSIONS` together. |
| `temi-mock-fallback.integration.test.ts` | All 8 Temi tools return `{ok:true, mock:true}` under `cfg.temi.mockMode=true`. With `mockMode=false` and a rejected `fetch`, `navigate_to` surfaces `{ok:false, error:...}` instead of throwing. |
| `research-arxiv.integration.test.ts` | `research_search_works` parses a canned arXiv Atom XML feed (embedded in the test) into `{title,url,abstract,year}`. Error paths (`fetch` throws / non-ok) resolve to `{works: []}` without throwing. |

## Adding a new integration test

1. Copy `_template.integration.test.ts` to `<your-feature>.integration.test.ts`.
2. Use the helpers already in `tests/helpers/`:
   - `createFakeConfig(overrides?)` — full `ClassmateConfig` with all 22 table
     IDs pre-set and `temi.mockMode=true` by default.
   - `createFakeApi({ config })` — yields `{ api, tools, services, commands,
     logs }`. Tools go in `tools` keyed by tool name; call `.execute(input)`
     and get the tool's raw payload back.
   - `createMockFeishuClient()` — mock Feishu SDK with call-log arrays. Wire
     it up via `vi.mock('../../src/util/feishu-api.js', ...)` when your tool
     writes to Bitable.
3. If your tool owns module-level state (like supervision sessions or the chat
   throttle cache), reset it in `beforeEach` — exported helpers such as
   `clearChatInteractionCache()` and `endSupervisionSession(id)` exist for
   exactly this.
4. When your tool calls global `fetch`, stub it with `vi.stubGlobal('fetch',
   vi.fn())` in `beforeEach` and `vi.unstubAllGlobals()` in `afterEach` —
   never let a test hit the real network.
5. Keep assertions structural where possible (e.g. `expect(res.ok).toBe(true)`,
   `expect(Array.isArray(res.works)).toBe(true)`) so innocuous copy changes
   don't trigger false regressions, but pin the things that are load-bearing
   for agents (option lists, enum values, error shape).
