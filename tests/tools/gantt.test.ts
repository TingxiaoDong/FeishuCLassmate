/**
 * Tests for gantt tools:
 *   - feishu_classmate_gantt_create
 *   - feishu_classmate_gantt_update_progress
 *   - feishu_classmate_gantt_list_today_nodes
 */
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { createFakeConfig } from '../helpers/fake-config.js';
import { createFakeApi, type ToolDef } from '../helpers/fake-api.js';
import { createMockFeishuClient } from '../helpers/mock-feishu-client.js';
import { registerGanttCreate } from '../../src/tools/gantt/create.js';
import { registerGanttUpdateProgress } from '../../src/tools/gantt/update-progress.js';
import { registerGanttListTodayNodes } from '../../src/tools/gantt/list-today-nodes.js';

// ---------------------------------------------------------------------------
// Module mock — vi.mock hoisted; holder is mutable so beforeEach can swap it.
// ---------------------------------------------------------------------------
const mockClientHolder = { client: createMockFeishuClient().client };

vi.mock('../../src/util/feishu-api.js', () => ({
  getFeishuClient: () => mockClientHolder.client,
  clearFeishuClientCache: vi.fn(),
}));

// ---------------------------------------------------------------------------
// feishu_classmate_gantt_create
// ---------------------------------------------------------------------------

describe('feishu_classmate_gantt_create', () => {
  let mock: ReturnType<typeof createMockFeishuClient>;

  beforeEach(() => {
    mock = createMockFeishuClient();
    mockClientHolder.client = mock.client;
  });

  it('batch-creates exactly as many records as milestones provided', async () => {
    const config = createFakeConfig();
    const { api, tools } = createFakeApi({ config });
    registerGanttCreate(api as never);
    const create = tools.get('feishu_classmate_gantt_create') as ToolDef;

    const milestones = [
      { milestone: '文献调研', due_date_iso: '2026-05-01' },
      { milestone: '原型跑通', due_date_iso: '2026-06-01' },
      { milestone: '论文初稿', due_date_iso: '2026-07-01' },
    ];

    const result = await create.execute({
      project_id: 'proj_abc',
      owner_open_id: 'ou_student1',
      milestones,
    }) as Record<string, unknown>;

    expect(result.ok).toBe(true);
    expect((result.gantt_ids as string[]).length).toBe(3);
    expect(mock.calls.batchCreateRecords).toHaveLength(1);
    const [, , records] = mock.calls.batchCreateRecords[0];
    expect(records.length).toBe(3);
  });

  it('records carry the correct project_id and initial status=未开始', async () => {
    const config = createFakeConfig();
    const { api, tools } = createFakeApi({ config });
    registerGanttCreate(api as never);
    const create = tools.get('feishu_classmate_gantt_create') as ToolDef;

    await create.execute({
      project_id: 'proj_xyz',
      owner_open_id: 'ou_student2',
      milestones: [{ milestone: '实验验证', due_date_iso: '2026-05-15' }],
    });

    const [, , records] = mock.calls.batchCreateRecords[0];
    expect(records[0].project_id).toBe('proj_xyz');
    expect(records[0].status).toBe('未开始');
    expect(records[0].progress).toBe(0);
  });

  it('returns ok=false when batchCreateRecords fails', async () => {
    mock.client.batchCreateRecords = vi.fn().mockResolvedValue({ ok: false, error: 'quota exceeded' });
    const config = createFakeConfig();
    const { api, tools } = createFakeApi({ config });
    registerGanttCreate(api as never);
    const create = tools.get('feishu_classmate_gantt_create') as ToolDef;

    const result = await create.execute({
      project_id: 'proj_fail',
      owner_open_id: 'ou_student3',
      milestones: [{ milestone: '阶段一', due_date_iso: '2026-05-01' }],
    }) as Record<string, unknown>;

    expect(result.ok).toBe(false);
    expect(result.error).toBe('quota exceeded');
  });
});

// ---------------------------------------------------------------------------
// feishu_classmate_gantt_update_progress
// ---------------------------------------------------------------------------

describe('feishu_classmate_gantt_update_progress', () => {
  let mock: ReturnType<typeof createMockFeishuClient>;

  beforeEach(() => {
    mock = createMockFeishuClient();
    mockClientHolder.client = mock.client;
  });

  function makeListWithRecord(fields: Record<string, unknown> = {}) {
    mock.client.listRecords = vi.fn().mockResolvedValue({
      ok: true,
      value: [{ record_id: 'rec_gantt_1', fields: { gantt_id: 'g_001', ...fields } }],
    });
  }

  it('auto-sets status=完成 when progress=100 and no status override', async () => {
    makeListWithRecord();
    const config = createFakeConfig();
    const { api, tools } = createFakeApi({ config });
    registerGanttUpdateProgress(api as never);
    const update = tools.get('feishu_classmate_gantt_update_progress') as ToolDef;

    const result = await update.execute({ gantt_id: 'g_001', progress: 100 }) as Record<string, unknown>;
    expect(result.ok).toBe(true);
    const [, , , fields] = mock.calls.updateRecord[0];
    expect(fields.status).toBe('完成');
    expect(fields.progress).toBe(100);
  });

  it('auto-sets status=进行中 when 0 < progress < 100 and no status override', async () => {
    makeListWithRecord();
    const config = createFakeConfig();
    const { api, tools } = createFakeApi({ config });
    registerGanttUpdateProgress(api as never);
    const update = tools.get('feishu_classmate_gantt_update_progress') as ToolDef;

    await update.execute({ gantt_id: 'g_001', progress: 50 });
    const [, , , fields] = mock.calls.updateRecord[0];
    expect(fields.status).toBe('进行中');
  });

  it('does not override status when caller provides one explicitly', async () => {
    makeListWithRecord();
    const config = createFakeConfig();
    const { api, tools } = createFakeApi({ config });
    registerGanttUpdateProgress(api as never);
    const update = tools.get('feishu_classmate_gantt_update_progress') as ToolDef;

    await update.execute({ gantt_id: 'g_001', progress: 100, status: '逾期' });
    const [, , , fields] = mock.calls.updateRecord[0];
    expect(fields.status).toBe('逾期');
  });

  it('returns ok=false with "not found" message when gantt_id does not exist', async () => {
    mock.client.listRecords = vi.fn().mockResolvedValue({ ok: true, value: [] });
    const config = createFakeConfig();
    const { api, tools } = createFakeApi({ config });
    registerGanttUpdateProgress(api as never);
    const update = tools.get('feishu_classmate_gantt_update_progress') as ToolDef;

    const result = await update.execute({ gantt_id: 'g_missing', progress: 50 }) as Record<string, unknown>;
    expect(result.ok).toBe(false);
    expect((result.error as string)).toContain('g_missing');
  });
});

// ---------------------------------------------------------------------------
// feishu_classmate_gantt_list_today_nodes
// ---------------------------------------------------------------------------

describe('feishu_classmate_gantt_list_today_nodes', () => {
  let mock: ReturnType<typeof createMockFeishuClient>;

  beforeEach(() => {
    mock = createMockFeishuClient();
    mockClientHolder.client = mock.client;
  });

  it('passes a filter containing due_date to listRecords', async () => {
    mock.client.listRecords = vi.fn().mockResolvedValue({ ok: true, value: [] });
    const config = createFakeConfig();
    const { api, tools } = createFakeApi({ config });
    registerGanttListTodayNodes(api as never);
    const list = tools.get('feishu_classmate_gantt_list_today_nodes') as ToolDef;

    await list.execute({ within_days: 0 });

    expect(mock.client.listRecords).toHaveBeenCalledOnce();
    const callArgs = (mock.client.listRecords as ReturnType<typeof vi.fn>).mock.calls[0] as [string, string, { filter?: string }];
    expect(callArgs[2]?.filter).toContain('due_date');
  });

  it('maps Bitable records into node objects with the correct shape', async () => {
    const dueTs = Date.now() + 3_600_000;
    mock.client.listRecords = vi.fn().mockResolvedValue({
      ok: true,
      value: [{
        record_id: 'rec_1',
        fields: {
          gantt_id: 'g_today',
          project_id: 'proj_test',
          owner_open_id: [{ id: 'ou_owner' }],
          milestone: '阶段一完成',
          due_date: dueTs,
          status: '进行中',
          progress: 40,
        },
      }],
    });

    const config = createFakeConfig();
    const { api, tools } = createFakeApi({ config });
    registerGanttListTodayNodes(api as never);
    const list = tools.get('feishu_classmate_gantt_list_today_nodes') as ToolDef;

    const result = await list.execute({ within_days: 1 }) as { nodes: unknown[] };
    expect(result.nodes).toHaveLength(1);
    const node = result.nodes[0] as Record<string, unknown>;
    expect(node.gantt_id).toBe('g_today');
    expect(node.owner_open_id).toBe('ou_owner');
    expect(node.progress).toBe(40);
    expect(typeof node.due_date_iso).toBe('string');
    expect(node.due_date_iso).toMatch(/^\d{4}-\d{2}-\d{2}$/);
  });

  it('returns empty nodes array when listRecords fails', async () => {
    mock.client.listRecords = vi.fn().mockResolvedValue({ ok: false, error: 'network error' });
    const config = createFakeConfig();
    const { api, tools } = createFakeApi({ config });
    registerGanttListTodayNodes(api as never);
    const list = tools.get('feishu_classmate_gantt_list_today_nodes') as ToolDef;

    const result = await list.execute({ within_days: 0 }) as { nodes: unknown[] };
    expect(result.nodes).toEqual([]);
  });
});
