/**
 * Tests for ensureBitableSchema (src/bitable/setup.ts):
 *   1. appToken missing → creates new Bitable app, then creates all 4 tables.
 *   2. appToken set and all tables exist → skips creation, resolves tableIds.
 *   3. Partial table existence → creates only the missing ones.
 */
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { createFakeConfig } from '../helpers/fake-config.js';
import { createFakeApi } from '../helpers/fake-api.js';
import { createMockFeishuClient } from '../helpers/mock-feishu-client.js';
import { ALL_TABLES } from '../../src/bitable/schema.js';
import { ensureBitableSchema } from '../../src/bitable/setup.js';

// ---------------------------------------------------------------------------
// Module mock
// ---------------------------------------------------------------------------
const mockClientHolder = { client: createMockFeishuClient().client };

vi.mock('../../src/util/feishu-api.js', () => ({
  getFeishuClient: () => mockClientHolder.client,
  clearFeishuClientCache: vi.fn(),
}));

const TABLE_COUNT = ALL_TABLES.length; // 4

// ---------------------------------------------------------------------------
// Scenario 1: no appToken → create app + all tables
// ---------------------------------------------------------------------------

describe('ensureBitableSchema — appToken missing', () => {
  let mock: ReturnType<typeof createMockFeishuClient>;

  beforeEach(() => {
    mock = createMockFeishuClient();
    mockClientHolder.client = mock.client;
  });

  it('calls createBitableApp exactly once', async () => {
    mock.client.listTables = vi.fn().mockResolvedValue({ ok: true, value: [] });

    const config = createFakeConfig({ bitable: { appToken: '', tableIds: {} } });
    const { api } = createFakeApi({ config });

    await ensureBitableSchema(api as never);

    expect(mock.calls.createBitableApp).toHaveLength(1);
  });

  it(`creates all ${TABLE_COUNT} tables when none pre-exist`, async () => {
    mock.client.listTables = vi.fn().mockResolvedValue({ ok: true, value: [] });

    const config = createFakeConfig({ bitable: { appToken: '', tableIds: {} } });
    const { api } = createFakeApi({ config });

    const result = await ensureBitableSchema(api as never);

    expect(mock.calls.createTable).toHaveLength(TABLE_COUNT);
    expect(result.created).toBe(true);
    expect(result.appToken).toBe('app_mock_token');
  });

  it('returns tableIds for all 4 logical keys', async () => {
    mock.client.listTables = vi.fn().mockResolvedValue({ ok: true, value: [] });

    const config = createFakeConfig({ bitable: { appToken: '', tableIds: {} } });
    const { api } = createFakeApi({ config });

    const result = await ensureBitableSchema(api as never);

    for (const table of ALL_TABLES) {
      expect(result.tableIds[table.key]).toBeDefined();
    }
  });

  it('throws when createBitableApp fails', async () => {
    mock.client.createBitableApp = vi.fn().mockResolvedValue({ ok: false, error: 'no permission', code: 99991 });

    const config = createFakeConfig({ bitable: { appToken: '', tableIds: {} } });
    const { api } = createFakeApi({ config });

    await expect(ensureBitableSchema(api as never)).rejects.toThrow('create bitable app failed');
  });
});

// ---------------------------------------------------------------------------
// Scenario 2: appToken set, all tables already exist → no creation calls
// ---------------------------------------------------------------------------

describe('ensureBitableSchema — appToken set, all tables present', () => {
  let mock: ReturnType<typeof createMockFeishuClient>;

  beforeEach(() => {
    mock = createMockFeishuClient();
    mockClientHolder.client = mock.client;
  });

  it('skips createBitableApp and createTable entirely', async () => {
    const existingTables = ALL_TABLES.map((t) => ({ table_id: `tbl_existing_${t.key}`, name: t.name }));
    mock.client.listTables = vi.fn().mockResolvedValue({ ok: true, value: existingTables });

    const config = createFakeConfig();
    const { api } = createFakeApi({ config });

    await ensureBitableSchema(api as never);

    expect(mock.calls.createBitableApp).toHaveLength(0);
    expect(mock.calls.createTable).toHaveLength(0);
  });

  it('resolves tableIds from the existing list without creating new tables', async () => {
    const existingTables = ALL_TABLES.map((t) => ({ table_id: `tbl_existing_${t.key}`, name: t.name }));
    mock.client.listTables = vi.fn().mockResolvedValue({ ok: true, value: existingTables });

    const config = createFakeConfig();
    const { api } = createFakeApi({ config });

    const result = await ensureBitableSchema(api as never);

    expect(result.tableIds['projects']).toBe('tbl_existing_projects');
    expect(result.tableIds['gantt']).toBe('tbl_existing_gantt');
    expect(result.tableIds['equipment']).toBe('tbl_existing_equipment');
    expect(result.tableIds['research']).toBe('tbl_existing_research');
    expect(result.created).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// Scenario 3: partial table existence → create only missing tables
// ---------------------------------------------------------------------------

describe('ensureBitableSchema — partial tables exist', () => {
  let mock: ReturnType<typeof createMockFeishuClient>;

  beforeEach(() => {
    mock = createMockFeishuClient();
    mockClientHolder.client = mock.client;
  });

  it('creates only the missing tables (Equipment + Research)', async () => {
    const existingTables = [
      { table_id: 'tbl_existing_projects', name: 'Projects' },
      { table_id: 'tbl_existing_gantt', name: 'Gantt' },
    ];
    mock.client.listTables = vi.fn().mockResolvedValue({ ok: true, value: existingTables });

    const config = createFakeConfig();
    const { api } = createFakeApi({ config });

    const result = await ensureBitableSchema(api as never);

    // schema.ts evolved — Projects/Gantt already exist, everything else gets created.
    const createdNames = mock.calls.createTable.map(([, name]) => name);
    expect(createdNames).toContain('Equipment');
    expect(createdNames).toContain('Research');
    expect(createdNames).not.toContain('Projects');
    expect(createdNames).not.toContain('Gantt');

    expect(result.tableIds['projects']).toBe('tbl_existing_projects');
    expect(result.tableIds['gantt']).toBe('tbl_existing_gantt');
  });

  it('records a warning (does not throw) when a single table creation fails', async () => {
    mock.client.listTables = vi.fn().mockResolvedValue({
      ok: true,
      value: [{ table_id: 'tbl_existing_projects', name: 'Projects' }],
    });
    let callCount = 0;
    mock.client.createTable = vi.fn().mockImplementation(async () => {
      callCount++;
      if (callCount === 1) return { ok: false, error: 'field type unsupported' };
      return { ok: true, value: { table_id: `tbl_mock_created_${callCount}` } };
    });

    const config = createFakeConfig();
    const { api } = createFakeApi({ config });

    const result = await ensureBitableSchema(api as never);

    // Should complete without throwing and collect warnings instead
    expect(result.warnings.length).toBeGreaterThanOrEqual(1);
    expect(result.warnings[0]).toContain('failed');
  });
});
