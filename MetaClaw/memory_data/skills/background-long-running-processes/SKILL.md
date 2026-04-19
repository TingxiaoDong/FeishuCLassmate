---
name: background-long-running-processes
description: Use when starting servers, daemons, or any process expected to run indefinitely. Always use `background=true` to prevent timeout failures.
category: automation
---

## Start Long-Running Processes in Background

1. Identify processes that will run indefinitely (servers, watchers, daemons)
2. Always use `exec background=true` when starting these processes
3. Set an appropriate `yieldMs` (e.g., 3000-5000) if you need initial output
4. Never set low timeouts (like 5 seconds) for long-running processes
5. After starting, use `process list` to verify the process is running
6. Use `process log` or `process poll` to check status

**Anti-pattern:** Running `python server.py` without background=true causes timeout after a few seconds, leaving the server in an unknown state.
