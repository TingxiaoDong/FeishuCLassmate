/**
 * Tests for equipment tools:
 *   - feishu_classmate_equipment_borrow
 *   - feishu_classmate_equipment_return
 */
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { createFakeConfig } from '../helpers/fake-config.js';
import { createFakeApi, type ToolDef } from '../helpers/fake-api.js';
import { createMockFeishuClient } from '../helpers/mock-feishu-client.js';
import { registerEquipmentBorrow } from '../../src/tools/equipment/borrow.js';
import { registerEquipmentReturn } from '../../src/tools/equipment/return.js';

// ---------------------------------------------------------------------------
// Module mock
// ---------------------------------------------------------------------------
const mockClientHolder = { client: createMockFeishuClient().client };

vi.mock('../../src/util/feishu-api.js', () => ({
  getFeishuClient: () => mockClientHolder.client,
  clearFeishuClientCache: vi.fn(),
}));

// ---------------------------------------------------------------------------
// Shared helper
// ---------------------------------------------------------------------------

function makeEquipmentRecord(fields: Record<string, unknown>) {
  return { record_id: 'rec_equip_1', fields };
}

// ---------------------------------------------------------------------------
// feishu_classmate_equipment_borrow
// ---------------------------------------------------------------------------

describe('feishu_classmate_equipment_borrow', () => {
  let mock: ReturnType<typeof createMockFeishuClient>;

  beforeEach(() => {
    mock = createMockFeishuClient();
    mockClientHolder.client = mock.client;
  });

  it('refuses to borrow when equipment state is already 借出', async () => {
    mock.client.listRecords = vi.fn().mockResolvedValue({
      ok: true,
      value: [makeEquipmentRecord({ equipment_id: 'eq_001', state: '借出' })],
    });

    const config = createFakeConfig();
    const { api, tools } = createFakeApi({ config });
    registerEquipmentBorrow(api as never);
    const borrow = tools.get('feishu_classmate_equipment_borrow') as ToolDef;

    const result = await borrow.execute({
      equipment_id: 'eq_001',
      borrower_open_id: 'ou_student1',
      expected_return_iso: '2026-05-01',
    }) as Record<string, unknown>;

    expect(result.ok).toBe(false);
    expect(result.error as string).toContain('借出');
    expect(mock.calls.updateRecord).toHaveLength(0);
  });

  it('writes state=借出, borrower_open_id, and timestamps on success', async () => {
    mock.client.listRecords = vi.fn().mockResolvedValue({
      ok: true,
      value: [makeEquipmentRecord({ equipment_id: 'eq_002', state: '在库' })],
    });

    const config = createFakeConfig();
    const { api, tools } = createFakeApi({ config });
    registerEquipmentBorrow(api as never);
    const borrow = tools.get('feishu_classmate_equipment_borrow') as ToolDef;

    const result = await borrow.execute({
      equipment_id: 'eq_002',
      borrower_open_id: 'ou_student2',
      expected_return_iso: '2026-06-01',
    }) as Record<string, unknown>;

    expect(result.ok).toBe(true);
    expect(result.record_id).toBe('rec_equip_1');

    expect(mock.calls.updateRecord).toHaveLength(1);
    const [, , , fields] = mock.calls.updateRecord[0];
    expect(fields.state).toBe('借出');
    expect(Array.isArray(fields.borrower_open_id)).toBe(true);
    expect((fields.borrower_open_id as Array<{ id: string }>)[0].id).toBe('ou_student2');
    expect(typeof fields.borrow_at).toBe('number');
    expect(typeof fields.expected_return).toBe('number');
  });

  it('returns ok=false when equipment_id not found in the table', async () => {
    mock.client.listRecords = vi.fn().mockResolvedValue({ ok: true, value: [] });

    const config = createFakeConfig();
    const { api, tools } = createFakeApi({ config });
    registerEquipmentBorrow(api as never);
    const borrow = tools.get('feishu_classmate_equipment_borrow') as ToolDef;

    const result = await borrow.execute({
      equipment_id: 'eq_unknown',
      borrower_open_id: 'ou_student3',
      expected_return_iso: '2026-05-10',
    }) as Record<string, unknown>;

    expect(result.ok).toBe(false);
    expect(result.error as string).toContain('eq_unknown');
  });

  it('returns ok=false and propagates error when listRecords itself fails', async () => {
    mock.client.listRecords = vi.fn().mockResolvedValue({ ok: false, error: 'token expired' });

    const config = createFakeConfig();
    const { api, tools } = createFakeApi({ config });
    registerEquipmentBorrow(api as never);
    const borrow = tools.get('feishu_classmate_equipment_borrow') as ToolDef;

    const result = await borrow.execute({
      equipment_id: 'eq_any',
      borrower_open_id: 'ou_student4',
      expected_return_iso: '2026-05-15',
    }) as Record<string, unknown>;

    expect(result.ok).toBe(false);
    expect(result.error).toBe('token expired');
  });
});

// ---------------------------------------------------------------------------
// feishu_classmate_equipment_return
// ---------------------------------------------------------------------------

describe('feishu_classmate_equipment_return', () => {
  let mock: ReturnType<typeof createMockFeishuClient>;

  beforeEach(() => {
    mock = createMockFeishuClient();
    mockClientHolder.client = mock.client;
  });

  it('detects overdue when current time exceeds expected_return', async () => {
    const overdueTs = Date.now() - 86_400_000; // 1 day ago
    mock.client.listRecords = vi.fn().mockResolvedValue({
      ok: true,
      value: [makeEquipmentRecord({
        equipment_id: 'eq_003',
        state: '借出',
        expected_return: overdueTs,
      })],
    });

    const config = createFakeConfig();
    const { api, tools } = createFakeApi({ config });
    registerEquipmentReturn(api as never);
    const ret = tools.get('feishu_classmate_equipment_return') as ToolDef;

    const result = await ret.execute({
      equipment_id: 'eq_003',
      observed_state: '正常',
    }) as Record<string, unknown>;

    expect(result.ok).toBe(true);
    expect(result.was_overdue).toBe(true);
  });

  it('was_overdue=false when returned before expected_return', async () => {
    const futureTs = Date.now() + 86_400_000;
    mock.client.listRecords = vi.fn().mockResolvedValue({
      ok: true,
      value: [makeEquipmentRecord({
        equipment_id: 'eq_004',
        state: '借出',
        expected_return: futureTs,
      })],
    });

    const config = createFakeConfig();
    const { api, tools } = createFakeApi({ config });
    registerEquipmentReturn(api as never);
    const ret = tools.get('feishu_classmate_equipment_return') as ToolDef;

    const result = await ret.execute({
      equipment_id: 'eq_004',
      observed_state: '正常',
    }) as Record<string, unknown>;

    expect(result.ok).toBe(true);
    expect(result.was_overdue).toBe(false);
  });

  it('sets state=维修 when observed_state=损坏', async () => {
    mock.client.listRecords = vi.fn().mockResolvedValue({
      ok: true,
      value: [makeEquipmentRecord({
        equipment_id: 'eq_005',
        state: '借出',
        expected_return: Date.now() + 86_400_000,
      })],
    });

    const config = createFakeConfig();
    const { api, tools } = createFakeApi({ config });
    registerEquipmentReturn(api as never);
    const ret = tools.get('feishu_classmate_equipment_return') as ToolDef;

    await ret.execute({ equipment_id: 'eq_005', observed_state: '损坏' });

    const [, , , fields] = mock.calls.updateRecord[0];
    expect(fields.state).toBe('维修');
  });

  it('sets state=在库 when observed_state=正常', async () => {
    mock.client.listRecords = vi.fn().mockResolvedValue({
      ok: true,
      value: [makeEquipmentRecord({
        equipment_id: 'eq_006',
        state: '借出',
        expected_return: Date.now() + 3_600_000,
      })],
    });

    const config = createFakeConfig();
    const { api, tools } = createFakeApi({ config });
    registerEquipmentReturn(api as never);
    const ret = tools.get('feishu_classmate_equipment_return') as ToolDef;

    await ret.execute({ equipment_id: 'eq_006', observed_state: '正常' });

    const [, , , fields] = mock.calls.updateRecord[0];
    expect(fields.state).toBe('在库');
  });

  it('clears borrower_open_id, borrow_at, and expected_return on return', async () => {
    mock.client.listRecords = vi.fn().mockResolvedValue({
      ok: true,
      value: [makeEquipmentRecord({
        equipment_id: 'eq_007',
        state: '借出',
        expected_return: Date.now() + 3_600_000,
        borrower_open_id: [{ id: 'ou_borrower' }],
      })],
    });

    const config = createFakeConfig();
    const { api, tools } = createFakeApi({ config });
    registerEquipmentReturn(api as never);
    const ret = tools.get('feishu_classmate_equipment_return') as ToolDef;

    await ret.execute({ equipment_id: 'eq_007', observed_state: '正常' });

    const [, , , fields] = mock.calls.updateRecord[0];
    expect(fields.borrow_at).toBeNull();
    expect(fields.expected_return).toBeNull();
    expect(Array.isArray(fields.borrower_open_id)).toBe(true);
    expect((fields.borrower_open_id as unknown[]).length).toBe(0);
  });
});
