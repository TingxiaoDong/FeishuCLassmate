/**
 * Thin wrapper around @larksuiteoapi/node-sdk.
 *
 * Why a wrapper?
 * - Single point to cache the tenant_access_token.
 * - Lets us stub in tests without monkey-patching the SDK.
 * - Converts SDK thrown errors into tagged Results for our tools.
 */

import * as lark from '@larksuiteoapi/node-sdk';
import type { ClassmateConfig } from '../config.js';

export type Result<T> = { ok: true; value: T } | { ok: false; error: string; code?: number };

export interface FeishuClientOptions {
  appId: string;
  appSecret: string;
  domain?: 'feishu' | 'lark';
}

const DOMAIN_MAP = {
  feishu: lark.Domain.Feishu,
  lark: lark.Domain.Lark,
};

export class FeishuClient {
  private sdk: lark.Client;
  private domain: 'feishu' | 'lark';

  constructor(opts: FeishuClientOptions) {
    this.domain = opts.domain ?? 'feishu';
    this.sdk = new lark.Client({
      appId: opts.appId,
      appSecret: opts.appSecret,
      domain: DOMAIN_MAP[this.domain],
      disableTokenCache: false,
    });
  }

  /** Expose raw SDK for advanced callers. */
  get raw(): lark.Client {
    return this.sdk;
  }

  // ---------- IM ----------

  async sendText(params: {
    receive_id: string;
    receive_id_type: 'open_id' | 'user_id' | 'chat_id' | 'union_id' | 'email';
    text: string;
  }): Promise<Result<{ message_id: string }>> {
    try {
      const res = await this.sdk.im.v1.message.create({
        params: { receive_id_type: params.receive_id_type },
        data: {
          receive_id: params.receive_id,
          msg_type: 'text',
          content: JSON.stringify({ text: params.text }),
        },
      });
      const msgId = res.data?.message_id ?? '';
      return { ok: true, value: { message_id: msgId } };
    } catch (err) {
      return toErrorResult(err);
    }
  }

  // ---------- Bitable apps ----------

  async createBitableApp(name: string, folderToken?: string): Promise<Result<{ app_token: string }>> {
    try {
      const res = await this.sdk.bitable.v1.app.create({
        data: { name, folder_token: folderToken },
      });
      const token = res.data?.app?.app_token ?? '';
      return { ok: true, value: { app_token: token } };
    } catch (err) {
      return toErrorResult(err);
    }
  }

  async listTables(appToken: string): Promise<Result<Array<{ table_id: string; name: string }>>> {
    try {
      const res = await this.sdk.bitable.v1.appTable.list({
        path: { app_token: appToken },
        params: { page_size: 100 },
      });
      const items = (res.data?.items ?? []).map((it) => ({
        table_id: it.table_id ?? '',
        name: it.name ?? '',
      }));
      return { ok: true, value: items };
    } catch (err) {
      return toErrorResult(err);
    }
  }

  async createTable(
    appToken: string,
    name: string,
    fields: Array<{ field_name: string; type: number; ui_type?: string; property?: unknown }>,
  ): Promise<Result<{ table_id: string }>> {
    try {
      const res = await this.sdk.bitable.v1.appTable.create({
        path: { app_token: appToken },
        data: {
          table: {
            name,
            default_view_name: '默认视图',
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            fields: fields as any,
          },
        },
      });
      return { ok: true, value: { table_id: res.data?.table_id ?? '' } };
    } catch (err) {
      return toErrorResult(err);
    }
  }

  async listFields(
    appToken: string,
    tableId: string,
  ): Promise<Result<Array<{ field_id: string; field_name: string; type: number }>>> {
    try {
      const res = await this.sdk.bitable.v1.appTableField.list({
        path: { app_token: appToken, table_id: tableId },
        params: { page_size: 100 },
      });
      const items = (res.data?.items ?? []).map((f) => ({
        field_id: f.field_id ?? '',
        field_name: f.field_name ?? '',
        type: f.type ?? 0,
      }));
      return { ok: true, value: items };
    } catch (err) {
      return toErrorResult(err);
    }
  }

  async createRecord(
    appToken: string,
    tableId: string,
    fields: Record<string, unknown>,
  ): Promise<Result<{ record_id: string }>> {
    try {
      const res = await this.sdk.bitable.v1.appTableRecord.create({
        path: { app_token: appToken, table_id: tableId },
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        data: { fields: fields as any },
      });
      return { ok: true, value: { record_id: res.data?.record?.record_id ?? '' } };
    } catch (err) {
      return toErrorResult(err);
    }
  }

  async listRecords(
    appToken: string,
    tableId: string,
    opts?: { filter?: string; sort?: string; pageSize?: number },
  ): Promise<Result<Array<{ record_id: string; fields: Record<string, unknown> }>>> {
    try {
      const res = await this.sdk.bitable.v1.appTableRecord.list({
        path: { app_token: appToken, table_id: tableId },
        params: {
          page_size: opts?.pageSize ?? 100,
          filter: opts?.filter,
          sort: opts?.sort,
        },
      });
      const items = (res.data?.items ?? []).map((r) => ({
        record_id: r.record_id ?? '',
        fields: (r.fields ?? {}) as Record<string, unknown>,
      }));
      return { ok: true, value: items };
    } catch (err) {
      return toErrorResult(err);
    }
  }

  async updateRecord(
    appToken: string,
    tableId: string,
    recordId: string,
    fields: Record<string, unknown>,
  ): Promise<Result<void>> {
    try {
      await this.sdk.bitable.v1.appTableRecord.update({
        path: { app_token: appToken, table_id: tableId, record_id: recordId },
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        data: { fields: fields as any },
      });
      return { ok: true, value: undefined };
    } catch (err) {
      return toErrorResult(err);
    }
  }

  async batchCreateRecords(
    appToken: string,
    tableId: string,
    records: Array<Record<string, unknown>>,
  ): Promise<Result<{ record_ids: string[] }>> {
    try {
      const res = await this.sdk.bitable.v1.appTableRecord.batchCreate({
        path: { app_token: appToken, table_id: tableId },
        data: {
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          records: records.map((fields) => ({ fields: fields as any })),
        },
      });
      const ids = (res.data?.records ?? []).map((r) => r.record_id ?? '');
      return { ok: true, value: { record_ids: ids } };
    } catch (err) {
      return toErrorResult(err);
    }
  }
}

/** Error → Result conversion preserving the Feishu error code when present. */
function toErrorResult<T>(err: unknown): Result<T> {
  if (err && typeof err === 'object' && 'response' in err) {
    // @ts-expect-error — SDK error shape
    const code = err.response?.data?.code;
    // @ts-expect-error — SDK error shape
    const msg = err.response?.data?.msg ?? String(err);
    return { ok: false, error: msg, code };
  }
  return { ok: false, error: String(err instanceof Error ? err.message : err) };
}

// ---------------------------------------------------------------------------
// Singleton cache keyed by (appId, domain) — Feishu's internal token cache is
// per-Client, so we keep one Client per credential pair.
// ---------------------------------------------------------------------------

const clientCache = new Map<string, FeishuClient>();

export function getFeishuClient(cfg: ClassmateConfig): FeishuClient {
  const key = `${cfg.feishu.appId}::${cfg.feishu.domain}`;
  let client = clientCache.get(key);
  if (!client) {
    client = new FeishuClient({
      appId: cfg.feishu.appId,
      appSecret: cfg.feishu.appSecret,
      domain: cfg.feishu.domain,
    });
    clientCache.set(key, client);
  }
  return client;
}

export function clearFeishuClientCache(): void {
  clientCache.clear();
}
