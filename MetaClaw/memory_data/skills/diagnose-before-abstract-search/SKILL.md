---
name: diagnose-before-abstract-search
description: When a robot command fails with a connection error, diagnose the specific issue (IP, port, protocol) before searching for alternative code paths.
category: robotics/execution
---

## Diagnose Robot Connection Errors Specifically

When receiving a "WebSocket Upgrade Failure" or connection error:

1. Check the error type first:
   - "404 WebSocket Upgrade Failure" → wrong endpoint or protocol mismatch
   - Connection refused → wrong IP/port

2. Verify the robot IP and port from context (e.g., 192.168.31.121:8175).

3. Report the specific diagnostic to the user: "Connection to temi at IP:PORT failed. Possible causes: robot offline, IP changed, or port mismatch."

4. If IP may have changed (as noted in config), ask user to confirm current IP.

**Anti-pattern:** Responding to a connection error by reading skill files or searching for .ts files—this doesn't fix the connection issue.
