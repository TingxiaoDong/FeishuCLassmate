/**
 * Tests for project tools:
 *   - feishu_classmate_project_ingest  (pure heuristic, no Feishu calls)
 *   - feishu_classmate_project_create  (writes to Bitable via FeishuClient)
 */
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { createFakeConfig } from '../helpers/fake-config.js';
import { createFakeApi, type ToolDef } from '../helpers/fake-api.js';
import { createMockFeishuClient } from '../helpers/mock-feishu-client.js';

// ---------------------------------------------------------------------------
// Module-level mock — vi.mock is hoisted before imports by Vitest.
// We use a shared holder so individual tests can swap the mock.
// ---------------------------------------------------------------------------

// Holder is declared here; getFeishuClient will always return holder.current.
const holder = { current: createMockFeishuClient().client };

vi.mock('../../src/util/feishu-api.js', () => ({
  getFeishuClient: () => holder.current,
  clearFeishuClientCache: vi.fn(),
}));

// Static imports happen after the vi.mock calls are processed.
import { registerProjectIngest } from '../../src/tools/project/ingest.js';
import { registerProjectCreate } from '../../src/tools/project/create.js';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function setupTools() {
  const config = createFakeConfig();
  const { api, tools } = createFakeApi({ config });
  registerProjectIngest(api as never);
  registerProjectCreate(api as never);
  return {
    ingest: tools.get('feishu_classmate_project_ingest') as ToolDef,
    create: tools.get('feishu_classmate_project_create') as ToolDef,
  };
}

// ---------------------------------------------------------------------------
// feishu_classmate_project_ingest
// ---------------------------------------------------------------------------

describe('feishu_classmate_project_ingest', () => {
  it('returns at least 1 milestone for a plain sentence', async () => {
    const { ingest } = setupTools();
    const result = await ingest.execute({
      raw_text: '我想做一个基于大模型的自动代码审查系统，帮助导师快速审查学生提交的代码。',
      default_visibility: '保密',
    }) as Record<string, unknown>;

    const milestones = result.milestones as Array<{ milestone: string; due_date_iso: string }>;
    expect(milestones.length).toBeGreaterThanOrEqual(1);
  });

  it('returns a non-empty title derived from the raw text', async () => {
    const { ingest } = setupTools();
    const result = await ingest.execute({
      raw_text: '智能实验室设备借还管理平台。基于RFID实现自动识别。',
      default_visibility: '可公开',
    }) as Record<string, unknown>;

    expect(typeof result.title).toBe('string');
    expect((result.title as string).length).toBeGreaterThan(0);
  });

  it('returns confidence > 0', async () => {
    const { ingest } = setupTools();
    const result = await ingest.execute({
      raw_text: '我要做强化学习环境仿真，用于机器人运动规划研究。',
      default_visibility: '保密',
    }) as Record<string, unknown>;

    expect(result.confidence).toBeGreaterThan(0);
  });

  it('passes through default_visibility to the result', async () => {
    const { ingest } = setupTools();
    const result = await ingest.execute({
      raw_text: '某个需要公开的项目描述。',
      default_visibility: '可公开',
    }) as Record<string, unknown>;

    expect(result.visibility).toBe('可公开');
  });

  it('milestone objects have milestone string and YYYY-MM-DD date', async () => {
    const { ingest } = setupTools();
    const result = await ingest.execute({
      raw_text: '多模态情感识别系统，计划三个月内完成。',
      default_visibility: '保密',
    }) as Record<string, unknown>;

    const milestones = result.milestones as Array<{ milestone: string; due_date_iso: string }>;
    for (const m of milestones) {
      expect(typeof m.milestone).toBe('string');
      expect(m.due_date_iso).toMatch(/^\d{4}-\d{2}-\d{2}$/);
    }
  });
});

// ---------------------------------------------------------------------------
// feishu_classmate_project_create
// ---------------------------------------------------------------------------

describe('feishu_classmate_project_create', () => {
  beforeEach(() => {
    holder.current = createMockFeishuClient().client;
  });

  it('calls createRecord once with the correct appToken and tableId', async () => {
    const mock = createMockFeishuClient();
    holder.current = mock.client;

    const config = createFakeConfig();
    const { api, tools } = createFakeApi({ config });
    registerProjectCreate(api as never);
    const create = tools.get('feishu_classmate_project_create') as ToolDef;

    await create.execute({
      title: '智能代码审查',
      owner_open_id: 'ou_student1',
    });

    expect(mock.calls.createRecord).toHaveLength(1);
    const [appToken, tableId] = mock.calls.createRecord[0];
    expect(appToken).toBe('test_bitable_token');
    expect(tableId).toBe('tbl_projects');
  });

  it('writes the title and status=规划中 into the record fields', async () => {
    const mock = createMockFeishuClient();
    holder.current = mock.client;

    const config = createFakeConfig();
    const { api, tools } = createFakeApi({ config });
    registerProjectCreate(api as never);
    const create = tools.get('feishu_classmate_project_create') as ToolDef;

    await create.execute({
      title: '机器人路径规划',
      owner_open_id: 'ou_student2',
    });

    const [, , fields] = mock.calls.createRecord[0];
    expect(fields.title).toBe('机器人路径规划');
    expect(fields.status).toBe('规划中');
  });

  it('returns ok=true and a project_id matching proj_* pattern', async () => {
    const mock = createMockFeishuClient();
    holder.current = mock.client;

    const config = createFakeConfig();
    const { api, tools } = createFakeApi({ config });
    registerProjectCreate(api as never);
    const create = tools.get('feishu_classmate_project_create') as ToolDef;

    const result = await create.execute({
      title: '深度学习图像分类',
      owner_open_id: 'ou_student3',
    }) as Record<string, unknown>;

    expect(result.ok).toBe(true);
    expect(typeof result.project_id).toBe('string');
    expect((result.project_id as string).startsWith('proj_')).toBe(true);
    expect(result.record_id).toBe('rec_mock');
  });

  it('returns ok=false with error when FeishuClient.createRecord fails', async () => {
    const mock = createMockFeishuClient({
      createRecord: vi.fn().mockResolvedValue({ ok: false, error: 'permission denied', code: 99991 }),
    });
    holder.current = mock.client;

    const config = createFakeConfig();
    const { api, tools } = createFakeApi({ config });
    registerProjectCreate(api as never);
    const create = tools.get('feishu_classmate_project_create') as ToolDef;

    const result = await create.execute({
      title: '任意项目',
      owner_open_id: 'ou_student4',
    }) as Record<string, unknown>;

    expect(result.ok).toBe(false);
    expect(typeof result.error).toBe('string');
  });
});
