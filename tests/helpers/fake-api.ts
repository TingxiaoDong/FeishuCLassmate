/**
 * Minimal OpenClawPluginApi-shaped object for unit tests.
 *
 * After the registerZodTool adapter, registered tools conform to OpenClaw's
 * real signature:  execute(toolCallId, params) => { content, details }.
 * This helper wraps that so tests can keep calling `tool.execute(input)`
 * and get the inner `details` payload back directly.
 */
import { vi } from 'vitest';
import type { ClassmateConfig } from '../../src/config.js';

interface RawToolDef {
  name: string;
  label?: string;
  description: string;
  parameters: unknown;
  execute: (toolCallId: string, params: unknown) => Promise<{ content: unknown; details: unknown }>;
}

/** Ergonomic wrapper — tests call `tool.execute(input)` and get the raw payload. */
export interface ToolDef {
  name: string;
  description: string;
  raw: RawToolDef;
  execute: (input: Record<string, unknown>) => Promise<unknown>;
}

export interface ServiceDef {
  id: string;
  [key: string]: unknown;
}

export interface CommandDef {
  [key: string]: unknown;
}

export interface FakeApi {
  api: unknown;
  tools: Map<string, ToolDef>;
  services: Map<string, ServiceDef>;
  commands: CommandDef[];
  logs: {
    debug: ReturnType<typeof vi.fn>;
    info: ReturnType<typeof vi.fn>;
    warn: ReturnType<typeof vi.fn>;
    error: ReturnType<typeof vi.fn>;
  };
}

export function createFakeApi(opts: { config: ClassmateConfig }): FakeApi {
  const tools = new Map<string, ToolDef>();
  const services = new Map<string, ServiceDef>();
  const commands: CommandDef[] = [];
  const logs = {
    debug: vi.fn(),
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
  };

  const api = {
    // getConfigFromApi reads api.pluginConfig (per src/config.ts)
    pluginConfig: opts.config as unknown,

    registerTool(def: RawToolDef) {
      tools.set(def.name, {
        name: def.name,
        description: def.description,
        raw: def,
        async execute(input: Record<string, unknown>) {
          const res = await def.execute('test-call', input);
          // Our adapter always returns {content, details}; details is the raw payload.
          return (res as { details: unknown }).details;
        },
      });
    },

    registerService(def: ServiceDef) {
      services.set(def.id, def);
    },

    registerCli(def: CommandDef, _opts?: unknown) {
      commands.push(def);
    },

    // Stubs for hooks; tests don't assert on these.
    on: vi.fn(),

    logger: logs,
  };

  return { api, tools, services, commands, logs };
}
