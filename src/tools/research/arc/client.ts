/**
 * HTTP client to the Python ARC sidecar (arc-sidecar/server.py).
 *
 * Mirrors temi/client.ts: falls back to mock responses when cfg.arc.mockMode
 * is true, so the research-arc tools can be exercised without the sidecar or
 * AutoResearchClaw installed. Mock mode keeps a tiny in-memory run registry so
 * start → status → fetch behaves coherently across calls within one process.
 */

import type { ClassmateConfig } from '../../../config.js';

export interface ArcResponse<T = Record<string, unknown>> {
  ok: boolean;
  mock: boolean;
  data?: T;
  error?: string;
}

interface ReqOpts {
  timeoutMs?: number;
}

// --- mock run registry (process-local; only used when cfg.arc.mockMode) ----- //

interface MockRun {
  run_id: string;
  topic: string;
  mode: string;
  hypothesis: string;
  plan_doc_url: string;
  startedAt: number;
}

const mockRuns = new Map<string, MockRun>();

/** A mock run reports "running" for the first 3s, then "completed". */
function mockRunPublic(r: MockRun): Record<string, unknown> {
  const elapsed = Date.now() - r.startedAt;
  const status = elapsed < 3_000 ? 'running' : 'completed';
  return {
    run_id: r.run_id,
    topic: r.topic,
    mode: r.mode,
    hypothesis: r.hypothesis,
    plan_doc_url: r.plan_doc_url,
    status,
    started_at: new Date(r.startedAt).toISOString(),
    finished_at: status === 'completed' ? new Date(r.startedAt + 3_000).toISOString() : '',
    return_code: status === 'completed' ? 0 : null,
    workdir: `(mock)/arc-runs/${r.run_id}`,
    error: '',
    log_tail: ['(mock) ARC pipeline simulated — set arc.mockMode=false for real runs.'],
  };
}

function mockDeliverables(r: MockRun): Record<string, unknown> {
  return {
    workdir: `(mock)/arc-runs/${r.run_id}`,
    files: {
      paper_draft: {
        path: `(mock)/arc-runs/${r.run_id}/paper_draft.md`,
        bytes: 256,
        preview: `# (mock) ${r.topic}\n\nHypothesis: ${r.hypothesis || '(none)'}\n\n## Abstract\n\n(mock) ARC was not actually run.`,
      },
      reviews: {
        path: `(mock)/arc-runs/${r.run_id}/reviews.md`,
        bytes: 80,
        preview: '# (mock) Peer Review\n\nScore: 6/10 — mock review, idea looks plausible.',
      },
    },
    dirs: {},
  };
}

function handleMock(
  path: string,
  method: 'GET' | 'POST',
  body: Record<string, unknown>,
): ArcResponse {
  // POST /runs — create a mock run
  if (method === 'POST' && path === '/runs') {
    const run_id = `arc_mock_${Date.now().toString(36)}`;
    const run: MockRun = {
      run_id,
      topic: String(body.topic ?? ''),
      mode: String(body.mode ?? 'auto'),
      hypothesis: String(body.hypothesis ?? ''),
      plan_doc_url: String(body.plan_doc_url ?? ''),
      startedAt: Date.now(),
    };
    mockRuns.set(run_id, run);
    return { ok: true, mock: true, data: { ok: true, run_id, status: 'running', mock: true } };
  }
  // GET /runs/{id}/result
  const resultMatch = path.match(/^\/runs\/(.+)\/result$/);
  if (method === 'GET' && resultMatch) {
    const run = mockRuns.get(resultMatch[1]);
    if (!run) return { ok: false, mock: true, error: `(mock) unknown run_id: ${resultMatch[1]}` };
    const pub = mockRunPublic(run);
    return {
      ok: true,
      mock: true,
      data: { ok: true, ...pub, deliverables: pub.status === 'completed' ? mockDeliverables(run) : null },
    };
  }
  // GET /runs/{id}
  const statusMatch = path.match(/^\/runs\/(.+)$/);
  if (method === 'GET' && statusMatch) {
    const run = mockRuns.get(statusMatch[1]);
    if (!run) return { ok: false, mock: true, error: `(mock) unknown run_id: ${statusMatch[1]}` };
    return { ok: true, mock: true, data: { ok: true, ...mockRunPublic(run) } };
  }
  return { ok: true, mock: true, data: { ok: true, note: `(mock) ${method} ${path}` } };
}

// --- real HTTP --------------------------------------------------------------- //

async function request<T = Record<string, unknown>>(
  cfg: ClassmateConfig,
  method: 'GET' | 'POST',
  path: string,
  body: Record<string, unknown> = {},
  opts: ReqOpts = {},
): Promise<ArcResponse<T>> {
  if (cfg.arc.mockMode) {
    return handleMock(path, method, body) as ArcResponse<T>;
  }

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), opts.timeoutMs ?? 15_000);
  try {
    const res = await fetch(`${cfg.arc.sidecarUrl}${path}`, {
      method,
      headers: method === 'POST' ? { 'content-type': 'application/json' } : undefined,
      body: method === 'POST' ? JSON.stringify(body) : undefined,
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

export const arcClient = {
  post: <T = Record<string, unknown>>(
    cfg: ClassmateConfig,
    path: string,
    body: Record<string, unknown>,
    opts?: ReqOpts,
  ) => request<T>(cfg, 'POST', path, body, opts),
  get: <T = Record<string, unknown>>(cfg: ClassmateConfig, path: string, opts?: ReqOpts) =>
    request<T>(cfg, 'GET', path, {}, opts),
};
