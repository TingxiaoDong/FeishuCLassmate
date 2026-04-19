---
name: diagnose-robot-command-failure-before-retry
description: Use when a robot movement command fails or the robot doesn't move. Always diagnose the root cause (connection state, WebSocket error, command parameters) before retrying.
category: robotics/execution
---

## Diagnose Before Retrying

When a robot fails to execute a command:

1. **Check connection state first**: Query `/status` or equivalent to confirm the robot is `connected: true` and not in an error state.
2. **Inspect WebSocket status**: Look for error messages like `"received 1001 (going away)"` — this indicates the connection was closed and needs re-establishment.
3. **Verify command parameters**: Confirm the location name exists in the robot's map and coordinates are valid.
4. **Wait for is_moving transition**: Poll until `is_moving` changes to `true` after issuing a goto command. If it stays `false`, the command was rejected.
5. **Report findings to user**: Tell the user what you discovered (e.g., "WebSocket disconnected, reconnecting" or "Location '入口' not found in map").

**Example diagnostic sequence:**
bash
# 1. Check if robot is still connected
curl -s http://localhost:8091/status
# Expected: connected:true, is_moving:false

# 2. If connected but not moving, retry once
curl -s -X POST http://localhost:8091/goto -H 'Content-Type: application/json' -d '{"location": "入口"}'

# 3. Poll for movement confirmation
curl -s http://localhost:8091/status | jq '.is_moving'
# If still false after 5s, report failure reason


**Anti-pattern:** Repeatedly sending the same goto command without checking why the previous command was rejected or the WebSocket disconnected.
