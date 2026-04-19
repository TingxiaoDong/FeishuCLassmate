---
name: interpret-protocol-level-errors
description: Use when receiving connection errors mentioning "WebSocket", "Upgrade", or "Sec-WebSocket-Key" to understand the protocol mismatch and take appropriate action.
category: robotics/execution
---

## Interpret Protocol-Level Errors

When the system returns errors related to WebSocket upgrades, follow this diagnostic sequence:

1. **Identify the error type**:
   - "missing Sec-WebSocket-Key": You're using HTTP to connect to a WebSocket endpoint
   - "404 WebSocket Upgrade Failure": The server doesn't support WebSocket on this endpoint
   - "going away": Connection was established but dropped

2. **Check the API documentation or available endpoints**:
   - `curl http://host:port/` or `curl http://host:port/api/` to see what endpoints exist
   - Look for `/ws/` or WebSocket-specific endpoints

3. **Match the protocol to the endpoint**:
   - If endpoint requires WebSocket, use `websocat`, `wscat`, or Python `websocket-client`
   - If endpoint is HTTP REST, use `curl` with JSON body

4. **If the error persists**, stop retrying the same approach and report to the user that the robot's API protocol doesn't match what's available.

**Anti-pattern:** Continuing to use `curl` with WebSocket headers when the error clearly indicates a protocol mismatch. The repeated "going away" errors mean the server is rejecting the connection type.
