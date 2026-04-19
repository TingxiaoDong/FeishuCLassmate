---
name: robot-connection-persist-before-retry
description: Use when a robot command fails with a WebSocket 1001 error or connection-drop error. Perform connectivity diagnostics before blindly retrying the same command.
category: robotics/execution
---

## Diagnose Robot Connection Errors Before Retry

When a robot command fails with a WebSocket disconnect (1001 going away) or similar connection errors:

1. **Check robot physical state first** - Verify the robot is powered on and not physically obstructed.
2. **Probe the service health** - Use `curl http://<host>:<port>/status` to confirm the API server is responsive.
3. **Inspect connection logs** - Review any recent logs for patterns (authentication expiry, timeout settings, resource exhaustion).
4. **Wait a deliberate interval** - If retrying, wait 5-10 seconds rather than immediately re-sending.
5. **Limit retry attempts** - Stop after 2-3 failed attempts and report to the user.

bash
# Diagnostic sequence before retry
curl -s http://127.0.0.1:8091/status
curl -s http://127.0.0.1:8091/connection
# Check logs for 1001 errors


**Anti-pattern:** Calling the same `/goto` or `/command` endpoint repeatedly when the WebSocket keeps disconnecting. This wastes time and may indicate an underlying issue that needs investigation, not retries.
