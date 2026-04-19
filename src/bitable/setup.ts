/**
 * Idempotent first-run setup of the four Bitable tables.
 *
 * Invoked by:
 *   - `/classmate setup-bitable` slash command
 *   - Plugin startup hook (best-effort; logs but doesn't throw if unconfigured)
 */

import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { homedir } from 'node:os';
import { dirname, join } from 'node:path';
import type { OpenClawPluginApi } from 'openclaw/plugin-sdk';
import { getConfigFromApi, assertFeishuConfigured, type ClassmateConfig } from '../config.js';
import { getFeishuClient } from '../util/feishu-api.js';
import { ALL_TABLES, type TableDef } from './schema.js';

export interface SetupResult {
  created: boolean;
  appToken: string;
  tableIds: Record<string, string>;
  warnings: string[];
}

/** Sidecar state file — survives restarts when api.setConfig is unavailable. */
const STATE_FILE = join(homedir(), '.openclaw', 'state', 'feishu-classmate.json');

interface StateFile {
  appId: string;
  appToken: string;
  tableIds: Record<string, string>;
  updatedAt: string;
}

function loadState(): StateFile | null {
  try {
    if (!existsSync(STATE_FILE)) return null;
    return JSON.parse(readFileSync(STATE_FILE, 'utf-8')) as StateFile;
  } catch {
    return null;
  }
}

function saveState(state: StateFile): void {
  mkdirSync(dirname(STATE_FILE), { recursive: true });
  writeFileSync(STATE_FILE, JSON.stringify(state, null, 2), 'utf-8');
}

/**
 * Ensure a Bitable app + all 4 tables exist. Returns the identifiers so the
 * caller can persist them into plugin config.
 *
 * Behavior:
 *   - If appToken is already configured: verify tables exist, create missing ones.
 *   - If not configured: create a new Bitable app in the user's drive root,
 *     then create all 4 tables.
 */
export async function ensureBitableSchema(
  api: OpenClawPluginApi,
  opts?: { labName?: string },
): Promise<SetupResult> {
  const cfg = getConfigFromApi(api);
  assertFeishuConfigured(cfg);
  const client = getFeishuClient(cfg);
  const warnings: string[] = [];

  let appToken = cfg.bitable.appToken;
  let created = false;
  const tableIds: Record<string, string> = { ...(cfg.bitable.tableIds ?? {}) };

  // Fallback to sidecar state when openclaw plugin config didn't survive
  // (api.setConfig is not available; see persistSetup).
  if (!appToken) {
    const state = loadState();
    if (state && state.appId === cfg.feishu.appId && state.appToken) {
      appToken = state.appToken;
      for (const [k, v] of Object.entries(state.tableIds ?? {})) tableIds[k] = v;
    }
  }

  // ---- Step 1: create app if missing ----
  if (!appToken) {
    const name = `${opts?.labName ?? cfg.labInfo.name} · 飞书同学数据`;
    const res = await client.createBitableApp(name);
    if (!res.ok) {
      throw new Error(`create bitable app failed: ${res.error} (code=${res.code ?? '?'})`);
    }
    appToken = res.value.app_token;
    created = true;
  }

  // ---- Step 2: list existing tables ----
  const listRes = await client.listTables(appToken);
  if (!listRes.ok) {
    throw new Error(`list tables failed: ${listRes.error}`);
  }
  const existingByName = new Map(listRes.value.map((t) => [t.name, t.table_id]));

  // ---- Step 3: create missing tables ----
  for (const table of ALL_TABLES) {
    const existing = existingByName.get(table.name);
    if (existing) {
      tableIds[table.key] = existing;
      continue;
    }

    const createRes = await client.createTable(
      appToken,
      table.name,
      table.fields.map((f) => ({
        field_name: f.field_name,
        type: f.type,
        property: f.property,
      })),
    );
    if (!createRes.ok) {
      warnings.push(`create table ${table.name} failed: ${createRes.error}`);
      continue;
    }
    tableIds[table.key] = createRes.value.table_id;
  }

  return {
    created,
    appToken,
    tableIds,
    warnings,
  };
}

/**
 * Persist setup result back into plugin config so subsequent calls skip creation.
 */
export async function persistSetup(
  api: OpenClawPluginApi,
  result: SetupResult,
): Promise<void> {
  // Best-effort path 1 — openclaw plugin config setter (if SDK exposes it).
  const configApi = api as unknown as {
    setConfig?: (patch: Record<string, unknown>) => Promise<void> | void;
  };
  if (typeof configApi.setConfig === 'function') {
    try {
      await configApi.setConfig({
        'bitable.appToken': result.appToken,
        'bitable.tableIds': result.tableIds,
      });
    } catch (err) {
      api.logger?.warn?.(`[feishu-classmate] setConfig failed: ${err}`);
    }
  }

  // Path 2 — always also write a sidecar state file. Survives restarts even
  // when the SDK config setter silently no-ops.
  try {
    const cfg = getConfigFromApi(api);
    saveState({
      appId: cfg.feishu.appId,
      appToken: result.appToken,
      tableIds: result.tableIds,
      updatedAt: new Date().toISOString(),
    });
    api.logger?.info?.(`[feishu-classmate] bitable state persisted: ${STATE_FILE}`);
  } catch (err) {
    api.logger?.warn?.(`[feishu-classmate] failed to write sidecar state: ${err}`);
  }
}

/** Helper used by tools to fetch the right table_id for a logical key. */
export function getTableId(
  cfg: ClassmateConfig,
  key:
    | 'projects'
    | 'gantt'
    | 'equipment'
    | 'research'
    | 'weekly_digests'
    | 'submissions'
    | 'standups'
    | 'tool_trace'
    | 'papers'
    | 'experiments'
    | 'reservations'
    | 'assignments'
    | 'training_runs'
    | 'checkpoints'
    | 'sim_runs'
    | 'skill_tree'
    | 'reading_group'
    | 'one_on_ones'
    | 'failure_archive'
    | 'lab_faq'
    | 'mentor_answers'
    | 'lab_memes'
    | 'task_decomposition',
): string {
  const id = cfg.bitable.tableIds?.[key];
  if (!id) {
    throw new Error(
      `bitable.tableIds.${key} missing. Run \`openclaw classmate setup-bitable\` first.`,
    );
  }
  return id;
}
