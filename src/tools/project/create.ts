/**
 * feishu_classmate_project_create — write a confirmed project to Bitable.
 */

import type { OpenClawPluginApi } from 'openclaw/plugin-sdk';
import { z } from 'zod';
import { getConfigFromApi } from '../../config.js';
import { getFeishuClient } from '../../util/feishu-api.js';
import { getTableId } from '../../bitable/setup.js';
import { registerZodTool } from '../../util/register-tool.js';

/** Accept common synonyms and normalize to the two Bitable option names. */
const VisibilityInput = z
  .union([z.enum(['可公开', '保密']), z.string()])
  .default('保密')
  .transform((v) => {
    const s = String(v ?? '').toLowerCase().trim();
    const publicAliases = ['可公开', '公开', 'public', 'open', 'team', 'org', 'visible', 'shared'];
    const privateAliases = ['保密', '私密', '私有', 'private', 'secret', 'internal', 'confidential'];
    if (publicAliases.some((a) => a.toLowerCase() === s)) return '可公开' as const;
    if (privateAliases.some((a) => a.toLowerCase() === s)) return '保密' as const;
    return '保密' as const;
  });

const CreateInput = z.object({
  title: z.string().min(1),
  owner_open_id: z.string().min(1),
  keywords: z.array(z.string()).default([]),
  visibility: VisibilityInput,
  abstract: z.string().default(''),
});

const CreateOutput = z.object({
  ok: z.boolean(),
  project_id: z.string().optional(),
  record_id: z.string().optional(),
  error: z.string().optional(),
});

export function registerProjectCreate(api: OpenClawPluginApi): void {
  registerZodTool(api, {
    name: 'feishu_classmate_project_create',
    description:
      '把学生确认后的项目写入 Projects 多维表。返回 project_id 供后续 gantt_create 使用。' +
      'visibility 只接受 "可公开" 或 "保密"(也允许 public/private 等同义词,会自动规范化)。',
    inputSchema: CreateInput,
    outputSchema: CreateOutput,
    async execute(input) {
      const cfg = getConfigFromApi(api);
      const client = getFeishuClient(cfg);
      const tableId = getTableId(cfg, 'projects');

      const projectId = `proj_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 6)}`;
      const now = Date.now();

      const res = await client.createRecord(cfg.bitable.appToken, tableId, {
        project_id: projectId,
        title: input.title,
        owner_open_id: [{ id: input.owner_open_id }],
        keywords: input.keywords,
        visibility: input.visibility,
        abstract_doc_token: input.abstract
          ? { link: `openclaw://abstract/${projectId}`, text: input.abstract.slice(0, 60) }
          : undefined,
        status: '规划中',
        created_at: now,
        updated_at: now,
      });

      if (!res.ok) {
        return { ok: false, error: res.error };
      }
      return { ok: true, project_id: projectId, record_id: res.value.record_id };
    },
  });
}
