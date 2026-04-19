---
name: recover-from-lost-shell-session
description: Use when a shell session disappears mid-command or reports 'No active session found'. Follow systematic recovery steps before reissuing commands.
category: automation
---

## Shell Session Recovery Protocol

1. On "No active session found" or session loss, check what was accomplished before the loss.
2. Parse any partial output that was returned before session died.
3. If session lost mid-command, restart with `--dry-run` to verify syntax first.
4. Before running npm/node commands that failed, verify:
   - `node_modules/` exists: `ls node_modules/ | head -5`
   - Package installed: `npm list <package-name>`
   - Correct working directory: `pwd`
5. If the original command failed with MODULE_NOT_FOUND, check package.json dependencies before re-running.

**Anti-pattern:** Immediately re-running the same command that failed without diagnosing why the session was lost.
