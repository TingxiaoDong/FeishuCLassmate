/**
 * feishu_classmate_chat_pick_topic — pick a conversation opener topic.
 * Weighted mix: 40% project / 30% research / 20% daily / 10% funny.
 */

import type { OpenClawPluginApi } from 'openclaw/plugin-sdk';
import { z } from 'zod';
import { getConfigFromApi } from '../../config.js';
import { getFeishuClient } from '../../util/feishu-api.js';
import { getTableId } from '../../bitable/setup.js';
import { registerZodTool } from '../../util/register-tool.js';

const Input = z.object({
  student_open_id: z.string().min(1),
});

const Source = z.enum(['project', 'research', 'daily', 'funny']);

const Output = z.object({
  ok: z.boolean(),
  topic: z.string().optional(),
  source: Source.optional(),
  hint: z.string().optional(),
  error: z.string().optional(),
});

const FUNNY_TEMPLATES = [
  '上周末实验室那个放了三天没人倒的咖啡杯,今天居然自己"长毛"了——你见过最离谱的实验室现象是啥?',
  '我刚数了数,你们组的贴纸墙又多了两张,是新到的 paper 还是新追的番?',
  '今天路过会议室发现白板上还写着三个月前的公式,你觉得该擦吗?',
  '刚才 Temi 的传感器把一盆绿萝识别成了"人",差点对它开口打招呼。',
];

export function registerChatPickTopic(api: OpenClawPluginApi): void {
  registerZodTool(api, {
    name: 'feishu_classmate_chat_pick_topic',
    description:
      '给一个学生随机挑一个闲聊话题(项目/研究/日常/趣事)。返回 topic + source + 一句 hint,供上层 agent 改写成自然开场白。',
    inputSchema: Input,
    outputSchema: Output,
    async execute(input) {
      const cfg = getConfigFromApi(api);
      const client = getFeishuClient(cfg);
      const roll = Math.random();

      // 40% project — exclude student's own projects and 保密 visibility.
      if (roll < 0.4) {
        try {
          const tableId = getTableId(cfg, 'projects');
          const res = await client.listRecords(cfg.bitable.appToken, tableId, { pageSize: 100 });
          if (res.ok) {
            const candidates = res.value.filter((r) => {
              const f = r.fields;
              // eslint-disable-next-line @typescript-eslint/no-explicit-any
              const ownerId = Array.isArray(f.owner_open_id) ? (f.owner_open_id as any[])[0]?.id : undefined;
              const visibility = typeof f.visibility === 'string' ? f.visibility : '';
              return ownerId && ownerId !== input.student_open_id && visibility !== '保密';
            });
            if (candidates.length > 0) {
              const pick = candidates[Math.floor(Math.random() * candidates.length)];
              const title = typeof pick.fields.title === 'string' ? pick.fields.title : '(未命名项目)';
              return {
                ok: true,
                topic: title,
                source: 'project' as const,
                hint: `同组的另一个项目「${title}」最近有新进展,聊聊这个能不能给对方一些启发。`,
              };
            }
          }
        } catch {
          /* fall through to next bucket */
        }
      }

      // 30% research — most recent Research row.
      if (roll < 0.7) {
        try {
          const tableId = getTableId(cfg, 'research');
          const res = await client.listRecords(cfg.bitable.appToken, tableId, {
            pageSize: 20,
            sort: '[{"field_name":"created_at","desc":true}]',
          });
          if (res.ok && res.value.length > 0) {
            const latest = res.value[0];
            const topic = typeof latest.fields.topic === 'string' ? latest.fields.topic : '最新研究';
            return {
              ok: true,
              topic,
              source: 'research' as const,
              hint: `昨晚我自己读了几篇关于「${topic}」的论文,有个点想分享给对方听听。`,
            };
          }
        } catch {
          /* fall through */
        }
      }

      // 20% daily — can't fetch Doc content inside a tool, return a hint.
      if (roll < 0.9) {
        const hasDoc = Boolean(cfg.docs.dailyRecord);
        return {
          ok: true,
          topic: '最近实验室的小事',
          source: 'daily' as const,
          hint: hasDoc
            ? '从【日常记录】Doc 里挑一条最近 7 天的有趣事件,用自己的话讲给对方听。'
            : '随意聊一件你最近"注意到"的实验室小事,自然就好。',
        };
      }

      // 10% funny template.
      const template = FUNNY_TEMPLATES[Math.floor(Math.random() * FUNNY_TEMPLATES.length)];
      return {
        ok: true,
        topic: 'funny_observation',
        source: 'funny' as const,
        hint: template,
      };
    },
  });
}
