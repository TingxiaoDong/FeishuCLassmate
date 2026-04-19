/**
 * feishu_classmate_research_search_works — query arXiv's Atom feed for recent
 * papers matching a topic. Parses XML inline to avoid extra deps.
 */

import type { OpenClawPluginApi } from 'openclaw/plugin-sdk';
import { z } from 'zod';
import { registerZodTool } from '../../util/register-tool.js';

const Input = z.object({
  topic: z.string().min(1),
  limit: z.number().int().min(1).max(20).default(5),
});

const Work = z.object({
  title: z.string(),
  url: z.string(),
  abstract: z.string(),
  year: z.number().int().optional(),
});

const Output = z.object({
  works: z.array(Work),
});

export function registerResearchSearchWorks(api: OpenClawPluginApi): void {
  registerZodTool(api, {
    name: 'feishu_classmate_research_search_works',
    description:
      '查询 arXiv 最近的相关论文。输入一个 topic,返回 {title, url, abstract, year} 列表。失败时返回空数组而非抛错。',
    inputSchema: Input,
    outputSchema: Output,
    async execute(input) {
      const q = encodeURIComponent(`all:${input.topic}`);
      const url =
        `http://export.arxiv.org/api/query?search_query=${q}` +
        `&start=0&max_results=${input.limit}&sortBy=submittedDate&sortOrder=descending`;

      try {
        const resp = await fetch(url);
        if (!resp.ok) return { works: [] };
        const xml = await resp.text();
        return { works: parseArxivAtom(xml, input.limit) };
      } catch {
        return { works: [] };
      }
    },
  });
}

/** Regex-based extractor; robust enough for well-formed arXiv Atom. */
function parseArxivAtom(xml: string, limit: number): Array<z.infer<typeof Work>> {
  const entries = xml.match(/<entry>[\s\S]*?<\/entry>/g) ?? [];
  const out: Array<z.infer<typeof Work>> = [];
  for (const entry of entries.slice(0, limit)) {
    const title = pick(entry, /<title>([\s\S]*?)<\/title>/)
      .replace(/\s+/g, ' ')
      .trim();
    const summary = pick(entry, /<summary>([\s\S]*?)<\/summary>/)
      .replace(/\s+/g, ' ')
      .trim();
    const published = pick(entry, /<published>([\s\S]*?)<\/published>/);
    // Prefer the abs link (rel="alternate") over the PDF one.
    const linkHref =
      entry.match(/<link[^>]*rel="alternate"[^>]*href="([^"]+)"/)?.[1] ??
      entry.match(/<id>([\s\S]*?)<\/id>/)?.[1]?.trim() ??
      '';
    const year = published ? Number(published.slice(0, 4)) : undefined;
    if (!title) continue;
    out.push({
      title,
      url: linkHref,
      abstract: summary,
      year: year && !Number.isNaN(year) ? year : undefined,
    });
  }
  return out;
}

function pick(src: string, re: RegExp): string {
  return src.match(re)?.[1] ?? '';
}
