/**
 * Adapter layer: register a zod-based tool against OpenClaw's TypeBox SDK.
 *
 * Our tools are written with zod schemas for ergonomics; OpenClaw's
 * `api.registerTool` expects:
 *   - `parameters: TSchema` (@sinclair/typebox)
 *   - `execute(toolCallId, params, signal?, onUpdate?) => AgentToolResult`
 *
 * This wrapper:
 *   1. Converts the zod input schema to a minimal TypeBox equivalent
 *      (enough for the agent to see field names + types; zod runtime
 *      validation still enforces constraints).
 *   2. Calls zod `safeParse` inside execute; returns a `formatToolError`
 *      payload on validation failure.
 *   3. Wraps successful payloads with `{content: [{type:'text', text:
 *      JSON.stringify(payload)}], details: payload}`.
 */

import type { OpenClawPluginApi } from 'openclaw/plugin-sdk';
import { Type, type TSchema } from '@sinclair/typebox';
import { z } from 'zod';

export interface ZodToolDef<TInput extends z.ZodTypeAny, TOutput> {
  name: string;
  label?: string;
  description: string;
  inputSchema: TInput;
  outputSchema?: z.ZodTypeAny;
  execute: (input: z.infer<TInput>) => Promise<TOutput>;
}

interface ToolResult {
  content: Array<{ type: 'text'; text: string }>;
  details: unknown;
}

export function registerZodTool<TInput extends z.ZodTypeAny, TOutput>(
  api: OpenClawPluginApi,
  def: ZodToolDef<TInput, TOutput>,
): void {
  let tbSchema: TSchema;
  try {
    tbSchema = zodToTypeBox(def.inputSchema);
  } catch (err) {
    // eslint-disable-next-line no-console -- surface schema conversion failures during register
    console.error(`[feishu-classmate] zodToTypeBox failed for tool ${def.name}:`, err);
    tbSchema = Type.Object({});
  }

  (api.registerTool as unknown as (t: Record<string, unknown>) => void)({
    name: def.name,
    label: def.label ?? def.name,
    description: def.description,
    parameters: tbSchema,
    async execute(_toolCallId: string, params: unknown): Promise<ToolResult> {
      const parsed = def.inputSchema.safeParse(params);
      if (!parsed.success) {
        return formatResult({
          ok: false,
          error: `input validation failed: ${parsed.error.message}`,
        });
      }
      try {
        const out = await def.execute(parsed.data);
        return formatResult(out);
      } catch (err) {
        return formatResult({
          ok: false,
          error: err instanceof Error ? err.message : String(err),
        });
      }
    },
  });
}

function formatResult(payload: unknown): ToolResult {
  const text = typeof payload === 'string' ? payload : JSON.stringify(payload, null, 2);
  return {
    content: [{ type: 'text', text }],
    details: payload,
  };
}

// ---------------------------------------------------------------------------
// zod v4 → TypeBox conversion
// ---------------------------------------------------------------------------
//
// zod v4 exposes its shape via `._def.type` (string discriminator) and
// type-specific siblings: `entries` for enum, `shape` for object,
// `element` for array, `innerType` for wrappers, `options` for union,
// `values` for literal.

interface ZodDefLike {
  type?: string;
  entries?: Record<string, string>;
  shape?: Record<string, z.ZodTypeAny>;
  element?: z.ZodTypeAny;
  innerType?: z.ZodTypeAny;
  options?: z.ZodTypeAny[];
  values?: Array<string | number | boolean>;
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function zodToTypeBox(schema: z.ZodTypeAny): TSchema {
  const def = (schema as unknown as { _def: ZodDefLike })._def;
  const description = (schema as { description?: string }).description;
  const opts = description ? { description } : {};

  switch (def?.type) {
    case 'string':
      return Type.String(opts);
    case 'number':
    case 'int':
      return Type.Number(opts);
    case 'bigint':
      return Type.Integer(opts);
    case 'boolean':
      return Type.Boolean(opts);
    case 'date':
      return Type.String({ ...opts, format: 'date-time' });
    case 'literal': {
      const values = def.values ?? [];
      if (values.length === 1) {
        return Type.Literal(values[0] as string | number | boolean, opts);
      }
      return Type.Union(
        values.map((v) => Type.Literal(v as string | number | boolean)),
        opts,
      );
    }
    case 'enum': {
      const entries = def.entries ?? {};
      const keys = Object.keys(entries);
      if (keys.length === 0) return Type.String(opts);
      if (keys.length === 1) return Type.Literal(entries[keys[0]], opts);
      return Type.Union(
        keys.map((k) => Type.Literal(entries[k])),
        opts,
      );
    }
    case 'array': {
      const inner = def.element as z.ZodTypeAny;
      return Type.Array(inner ? zodToTypeBox(inner) : Type.Any(), opts);
    }
    case 'object': {
      const shape = def.shape ?? {};
      const props: Record<string, TSchema> = {};
      const required: string[] = [];
      for (const [key, value] of Object.entries(shape)) {
        const innerType = (value as unknown as { _def?: ZodDefLike })._def?.type;
        const isOptional = innerType === 'optional' || innerType === 'default';
        const unwrapped = isOptional
          ? ((value as unknown as { _def: ZodDefLike })._def.innerType as z.ZodTypeAny)
          : value;
        props[key] = zodToTypeBox(unwrapped);
        if (!isOptional) required.push(key);
      }
      return Type.Object(props, { ...opts, required });
    }
    case 'optional':
    case 'default': {
      const inner = def.innerType as z.ZodTypeAny;
      return Type.Optional(inner ? zodToTypeBox(inner) : Type.Any());
    }
    case 'nullable': {
      const inner = def.innerType as z.ZodTypeAny;
      return Type.Union([inner ? zodToTypeBox(inner) : Type.Any(), Type.Null()], opts);
    }
    case 'union': {
      const options = def.options ?? [];
      return Type.Union(options.map(zodToTypeBox), opts);
    }
    default:
      return Type.Any(opts);
  }
}
