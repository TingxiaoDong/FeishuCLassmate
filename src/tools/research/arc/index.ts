/**
 * ARC tool group — async bridge to the AutoResearchClaw sidecar.
 *
 *   feishu_classmate_research_arc_start  — kick off a 23-stage validation run
 *   feishu_classmate_research_arc_status — poll run status
 *   feishu_classmate_research_arc_fetch  — collect deliverables once completed
 *
 * Used by the `research-collaboration-agent` skill to hand a finalized research
 * plan off to ARC for idea validation. See arc-sidecar/ for the Python shim.
 */

import type { OpenClawPluginApi } from 'openclaw/plugin-sdk';
import { registerResearchArcStart } from './start.js';
import { registerResearchArcStatus } from './status.js';
import { registerResearchArcFetch } from './fetch.js';

export function registerResearchArcTools(api: OpenClawPluginApi): void {
  registerResearchArcStart(api);
  registerResearchArcStatus(api);
  registerResearchArcFetch(api);
}
