---
name: automation-track-background-process-state
description: Use when launching background processes or long-running commands. Maintain a clear state map of which processes are running and their expected outcomes.
category: automation
---

## Track Background Process State

1. When launching a background process, immediately record: session ID, command purpose, and expected completion criteria.
2. Use `process poll` with a reasonable timeout to wait for completion before taking further actions.
3. Never start a new command that depends on a previous background process until the previous one has completed or been explicitly checked.
4. If a process shows "killed" or unexpected termination, investigate before proceeding.
5. Keep process state synchronized: if you reference a session ID, verify it's still valid.

**Example:**

# Start process and immediately track
Start: session=my-task-123, purpose=start-server, expected=port-8091-listening
Poll: session=my-task-123, timeout=10000
# Only proceed after confirmed completion


**Anti-pattern:** Starting multiple background commands in sequence without polling for completion, losing track of which process is which.
