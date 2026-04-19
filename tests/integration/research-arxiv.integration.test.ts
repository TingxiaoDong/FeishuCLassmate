/**
 * E2E integration: feishu_classmate_research_search_works
 *
 * Stubs global `fetch` with a canned arXiv Atom feed, then asserts the tool
 * parses it into {title, url, abstract, year} entries. Also covers the error
 * path: a throwing fetch must resolve with {works: []}, never re-throw.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { createFakeConfig } from '../helpers/fake-config.js';
import { createFakeApi, type ToolDef } from '../helpers/fake-api.js';
import { registerResearchSearchWorks } from '../../src/tools/research/search-works.js';

// ---------------------------------------------------------------------------
// Canned arXiv Atom XML. Three <entry> blocks so limit=3 gets all of them;
// trimmed to just the fields the parser cares about.
// ---------------------------------------------------------------------------

const CANNED_ARXIV_ATOM = `<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>ArXiv Query: reinforcement learning</title>
  <entry>
    <id>http://arxiv.org/abs/2601.00001v1</id>
    <updated>2026-04-10T12:00:00Z</updated>
    <published>2026-04-10T12:00:00Z</published>
    <title>Scalable RLHF with Offline Preferences</title>
    <summary>
      We study reinforcement learning from human feedback in an offline setting
      and propose a scalable algorithm with strong empirical gains.
    </summary>
    <author><name>Alice A.</name></author>
    <link href="http://arxiv.org/abs/2601.00001v1" rel="alternate" type="text/html"/>
    <link href="http://arxiv.org/pdf/2601.00001v1" rel="related" type="application/pdf"/>
  </entry>
  <entry>
    <id>http://arxiv.org/abs/2601.00002v2</id>
    <updated>2026-03-22T09:30:00Z</updated>
    <published>2026-03-22T09:30:00Z</published>
    <title>Proximal Policy Optimization Revisited</title>
    <summary>
      We revisit PPO for continuous control under distributional shift and
      introduce a variance-reduced variant.
    </summary>
    <author><name>Bob B.</name></author>
    <link href="http://arxiv.org/abs/2601.00002v2" rel="alternate" type="text/html"/>
  </entry>
  <entry>
    <id>http://arxiv.org/abs/2502.12345v1</id>
    <updated>2025-11-05T00:00:00Z</updated>
    <published>2025-11-05T00:00:00Z</published>
    <title>Curriculum Learning for Sim-to-Real Transfer</title>
    <summary>
      A curriculum approach bridges the sim-to-real gap for dexterous
      manipulation tasks.
    </summary>
    <author><name>Carol C.</name></author>
    <link href="http://arxiv.org/abs/2502.12345v1" rel="alternate" type="text/html"/>
  </entry>
</feed>
`;

function setup() {
  const config = createFakeConfig();
  const { api, tools } = createFakeApi({ config });
  registerResearchSearchWorks(api as never);
  return tools.get('feishu_classmate_research_search_works') as ToolDef;
}

describe('integration: feishu_classmate_research_search_works', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('parses a canned arXiv Atom feed into {title,url,abstract,year} entries', async () => {
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      status: 200,
      text: async () => CANNED_ARXIV_ATOM,
    });

    const tool = setup();
    const result = (await tool.execute({ topic: 'reinforcement learning', limit: 3 })) as {
      works: Array<{ title: string; url: string; abstract: string; year?: number }>;
    };

    expect(Array.isArray(result.works)).toBe(true);
    expect(result.works).toHaveLength(3);

    const [w1, w2, w3] = result.works;

    expect(w1.title).toContain('Scalable RLHF');
    expect(w1.url).toBe('http://arxiv.org/abs/2601.00001v1');
    expect(w1.abstract.toLowerCase()).toContain('reinforcement learning');
    expect(w1.year).toBe(2026);

    expect(w2.title).toContain('Proximal Policy Optimization');
    expect(w2.url).toBe('http://arxiv.org/abs/2601.00002v2');
    expect(w2.year).toBe(2026);

    expect(w3.title).toContain('Curriculum Learning');
    expect(w3.url).toBe('http://arxiv.org/abs/2502.12345v1');
    expect(w3.year).toBe(2025);

    // fetch must be hit exactly once, with an arxiv.org query URL.
    expect((globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls.length).toBe(1);
    const calledUrl = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0][0] as string;
    expect(calledUrl).toContain('export.arxiv.org');
    expect(calledUrl).toContain('reinforcement');
  });

  it('returns {works: []} (no throw) when fetch rejects', async () => {
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockRejectedValue(new Error('DNS error'));

    const tool = setup();
    const result = (await tool.execute({ topic: 'anything', limit: 3 })) as {
      works: unknown[];
    };

    expect(result.works).toEqual([]);
  });

  it('returns {works: []} when fetch responds non-ok', async () => {
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: false,
      status: 500,
      text: async () => 'server error',
    });

    const tool = setup();
    const result = (await tool.execute({ topic: 'anything', limit: 3 })) as {
      works: unknown[];
    };

    expect(result.works).toEqual([]);
  });
});
