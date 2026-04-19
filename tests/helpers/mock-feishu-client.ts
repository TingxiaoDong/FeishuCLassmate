/**
 * Factory for a mock FeishuClient that never hits real servers.
 * Call-site assertions can inspect `.calls.<method>` arrays.
 */
import { vi } from 'vitest';
import type { Result } from '../../src/util/feishu-api.js';

export interface MockCallLog {
  createRecord: Array<[string, string, Record<string, unknown>]>;
  listRecords: Array<[string, string, unknown]>;
  updateRecord: Array<[string, string, string, Record<string, unknown>]>;
  batchCreateRecords: Array<[string, string, Array<Record<string, unknown>>]>;
  createBitableApp: Array<[string, string | undefined]>;
  listTables: Array<[string]>;
  createTable: Array<[string, string, unknown[]]>;
  sendText: Array<[unknown]>;
}

export interface MockFeishuClient {
  createRecord: ReturnType<typeof vi.fn>;
  listRecords: ReturnType<typeof vi.fn>;
  updateRecord: ReturnType<typeof vi.fn>;
  batchCreateRecords: ReturnType<typeof vi.fn>;
  createBitableApp: ReturnType<typeof vi.fn>;
  listTables: ReturnType<typeof vi.fn>;
  createTable: ReturnType<typeof vi.fn>;
  sendText: ReturnType<typeof vi.fn>;
}

/**
 * Create a mock FeishuClient.
 * Default return values are `{ok: true, value: ...}` stubs.
 * Override individual methods by passing replacement `vi.fn()` impls.
 */
export function createMockFeishuClient(overrides?: Partial<MockFeishuClient>): {
  client: MockFeishuClient;
  calls: MockCallLog;
} {
  const calls: MockCallLog = {
    createRecord: [],
    listRecords: [],
    updateRecord: [],
    batchCreateRecords: [],
    createBitableApp: [],
    listTables: [],
    createTable: [],
    sendText: [],
  };

  const client: MockFeishuClient = {
    createRecord: vi.fn(async (appToken: string, tableId: string, fields: Record<string, unknown>): Promise<Result<{ record_id: string }>> => {
      calls.createRecord.push([appToken, tableId, fields]);
      return { ok: true, value: { record_id: 'rec_mock' } };
    }),

    listRecords: vi.fn(async (appToken: string, tableId: string, opts?: unknown): Promise<Result<Array<{ record_id: string; fields: Record<string, unknown> }>>> => {
      calls.listRecords.push([appToken, tableId, opts]);
      return { ok: true, value: [] };
    }),

    updateRecord: vi.fn(async (appToken: string, tableId: string, recordId: string, fields: Record<string, unknown>): Promise<Result<void>> => {
      calls.updateRecord.push([appToken, tableId, recordId, fields]);
      return { ok: true, value: undefined };
    }),

    batchCreateRecords: vi.fn(async (appToken: string, tableId: string, records: Array<Record<string, unknown>>): Promise<Result<{ record_ids: string[] }>> => {
      calls.batchCreateRecords.push([appToken, tableId, records]);
      const ids = records.map((_, i) => `rec_mock_${i}`);
      return { ok: true, value: { record_ids: ids } };
    }),

    createBitableApp: vi.fn(async (name: string, folderToken?: string): Promise<Result<{ app_token: string }>> => {
      calls.createBitableApp.push([name, folderToken]);
      return { ok: true, value: { app_token: 'app_mock_token' } };
    }),

    listTables: vi.fn(async (appToken: string): Promise<Result<Array<{ table_id: string; name: string }>>> => {
      calls.listTables.push([appToken]);
      return { ok: true, value: [] };
    }),

    createTable: vi.fn(async (appToken: string, name: string, fields: unknown[]): Promise<Result<{ table_id: string }>> => {
      calls.createTable.push([appToken, name, fields]);
      return { ok: true, value: { table_id: `tbl_mock_${name}` } };
    }),

    sendText: vi.fn(async (params: unknown): Promise<Result<{ message_id: string }>> => {
      calls.sendText.push([params]);
      return { ok: true, value: { message_id: 'msg_mock' } };
    }),

    ...overrides,
  };

  return { client, calls };
}
