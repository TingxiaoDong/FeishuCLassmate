/**
 * E2E integration: feishu_classmate_data_layout
 *
 * End-to-end flow: tool registration → tool invocation → schema derivation
 * from src/bitable/schema.ts. Guards against regressions where a schema enum
 * option set gets renamed or a table key drops out of `ALL_TABLES`.
 *
 * No network calls. Uses a fake OpenClaw api + a seeded mock Feishu client.
 * (The mock client isn't actually used by data-layout, but it's wired up to
 * prove the `api + client + config` triple is self-consistent.)
 */
import { describe, expect, it } from 'vitest';
import { createFakeConfig } from '../helpers/fake-config.js';
import { createFakeApi, type ToolDef } from '../helpers/fake-api.js';
import { createMockFeishuClient } from '../helpers/mock-feishu-client.js';
import { registerDataLayout } from '../../src/tools/data-layout.js';
import { ALL_TABLES } from '../../src/bitable/schema.js';

/** Build a full tableIds map covering every entry in ALL_TABLES. */
function seedAllTableIds(): Record<string, string> {
  const ids: Record<string, string> = {};
  for (const t of ALL_TABLES) {
    ids[t.key] = `tbl_seed_${t.key}`;
  }
  return ids;
}

describe('integration: feishu_classmate_data_layout', () => {
  it('returns app_token + tables + notes with all 20+ seeded tables', async () => {
    // Seed the mock client just to prove the full wiring works; data-layout
    // doesn't touch it but a real agent flow would have one available.
    const { client } = createMockFeishuClient();
    expect(client).toBeDefined();

    const config = createFakeConfig({
      bitable: { appToken: 'app_integration_token', tableIds: seedAllTableIds() },
    });
    const { api, tools } = createFakeApi({ config });
    registerDataLayout(api as never);

    const tool = tools.get('feishu_classmate_data_layout') as ToolDef;
    expect(tool).toBeDefined();

    const result = (await tool.execute({})) as Record<string, unknown>;

    expect(result).toHaveProperty('app_token', 'app_integration_token');
    expect(result).toHaveProperty('tables');
    expect(typeof result.notes).toBe('string');
    expect((result.notes as string).length).toBeGreaterThan(0);

    const tables = result.tables as Record<
      string,
      { table_id: string; fields: Array<{ name: string; type: number; options?: string[] }> }
    >;
    // One entry per logical table in ALL_TABLES (>= 20).
    expect(Object.keys(tables).length).toBeGreaterThanOrEqual(20);
    for (const t of ALL_TABLES) {
      expect(tables[t.key]).toBeDefined();
      expect(tables[t.key].table_id).toBe(`tbl_seed_${t.key}`);
    }
  });

  it('projects.visibility has options ["可公开","保密"]', async () => {
    const config = createFakeConfig({
      bitable: { appToken: 'app_integration_token', tableIds: seedAllTableIds() },
    });
    const { api, tools } = createFakeApi({ config });
    registerDataLayout(api as never);
    const tool = tools.get('feishu_classmate_data_layout') as ToolDef;

    const result = (await tool.execute({})) as {
      tables: Record<string, { fields: Array<{ name: string; options?: string[] }> }>;
    };

    const visibility = result.tables.projects.fields.find((f) => f.name === 'visibility');
    expect(visibility).toBeDefined();
    expect(visibility!.options).toEqual(['可公开', '保密']);
  });

  it('equipment.state has options ["在库","借出","维修","丢失"]', async () => {
    const config = createFakeConfig({
      bitable: { appToken: 'app_integration_token', tableIds: seedAllTableIds() },
    });
    const { api, tools } = createFakeApi({ config });
    registerDataLayout(api as never);
    const tool = tools.get('feishu_classmate_data_layout') as ToolDef;

    const result = (await tool.execute({})) as {
      tables: Record<string, { fields: Array<{ name: string; options?: string[] }> }>;
    };

    const state = result.tables.equipment.fields.find((f) => f.name === 'state');
    expect(state).toBeDefined();
    expect(state!.options).toEqual(['在库', '借出', '维修', '丢失']);
  });

  it('omits tables from the result when their tableId is not configured', async () => {
    // Start from fake defaults, then null out every tableId except projects +
    // equipment. (fake-config merges so we can't simply pass a short map.)
    const config = createFakeConfig({
      bitable: {
        appToken: 'app_integration_token',
        tableIds: { projects: 'tbl_p', equipment: 'tbl_e' },
      },
    });
    config.bitable.tableIds = { projects: 'tbl_p', equipment: 'tbl_e' };
    const { api, tools } = createFakeApi({ config });
    registerDataLayout(api as never);
    const tool = tools.get('feishu_classmate_data_layout') as ToolDef;

    const result = (await tool.execute({})) as {
      tables: Record<string, unknown>;
    };
    expect(Object.keys(result.tables).sort()).toEqual(['equipment', 'projects']);
  });
});
