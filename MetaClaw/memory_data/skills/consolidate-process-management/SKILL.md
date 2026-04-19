---
name: consolidate-process-management
description: Use when multiple background processes are running. Consolidate into a single workflow to avoid process sprawl and confusion about which session holds the relevant output.
category: automation
---

## Consolidate Process Management

1. **List all active processes** with `process list` before starting new ones
2. **Kill stale sessions** that are no longer needed: `process kill <sessionId>`
3. **Use a single session** for related operations (edit → restart → test)
4. **Chain commands** in one call when possible: `sleep 4 && curl ... && curl ...`
5. **Log results** to a variable or file instead of spawning multiple sessions

bash
# Good: One session for edit-restart-test cycle
process write sessionId=main <<< 'cd /path && make restart && sleep 4 && curl test'
process poll sessionId=main timeout=15000

# Bad: Multiple sessions (gentle-summit, clear-canyon) for same workflow


**Anti-pattern:** Creating new process sessions for each sub-step, losing track of which session contains which output.
