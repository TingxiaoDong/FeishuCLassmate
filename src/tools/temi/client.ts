/**
 * HTTP client to the Python Temi sidecar.
 *
 * Falls back to mock responses when cfg.temi.mockMode = true, so tools can
 * always be called during Phase 1 development without the real robot.
 */

import type { ClassmateConfig } from '../../config.js';

export interface SidecarResponse<T = Record<string, unknown>> {
  ok: boolean;
  mock: boolean;
  data?: T;
  error?: string;
}

interface PostOpts {
  timeoutMs?: number;
  mockReturn?: Record<string, unknown>;
}

async function post<T = Record<string, unknown>>(
  cfg: ClassmateConfig,
  path: string,
  body: Record<string, unknown>,
  opts: PostOpts = {},
): Promise<SidecarResponse<T>> {
  if (cfg.temi.mockMode) {
    return {
      ok: true,
      mock: true,
      data: (opts.mockReturn as T) ?? ({ note: `(mock) ${path} ${JSON.stringify(body)}` } as unknown as T),
    };
  }

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), opts.timeoutMs ?? 15_000);
  try {
    const res = await fetch(`${cfg.temi.sidecarUrl}${path}`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(body),
      signal: controller.signal,
    });
    if (!res.ok) {
      return { ok: false, mock: false, error: `HTTP ${res.status}: ${await res.text()}` };
    }
    const data = (await res.json()) as T;
    return { ok: true, mock: false, data };
  } catch (err) {
    return { ok: false, mock: false, error: err instanceof Error ? err.message : String(err) };
  } finally {
    clearTimeout(timer);
  }
}

async function get<T = Record<string, unknown>>(
  cfg: ClassmateConfig,
  path: string,
  opts: PostOpts = {},
): Promise<SidecarResponse<T>> {
  if (cfg.temi.mockMode) {
    return { ok: true, mock: true, data: (opts.mockReturn as T) ?? ({} as T) };
  }
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), opts.timeoutMs ?? 5_000);
  try {
    const res = await fetch(`${cfg.temi.sidecarUrl}${path}`, {
      method: 'GET',
      signal: controller.signal,
    });
    if (!res.ok) {
      return { ok: false, mock: false, error: `HTTP ${res.status}: ${await res.text()}` };
    }
    return { ok: true, mock: false, data: (await res.json()) as T };
  } catch (err) {
    return { ok: false, mock: false, error: err instanceof Error ? err.message : String(err) };
  } finally {
    clearTimeout(timer);
  }
}

export const temiClient = {
  post,
  get,
};
