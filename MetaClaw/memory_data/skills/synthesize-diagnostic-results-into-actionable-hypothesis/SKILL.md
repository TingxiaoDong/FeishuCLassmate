---
name: synthesize-diagnostic-results-into-actionable-hypothesis
description: Use when multiple diagnostic commands have been run and their outputs need to be combined into a coherent hypothesis and next action.
category: automation
---

## Synthesize Diagnostic Results into Actionable Hypothesis

1. **Collect all outputs** from ping, nc, curl, WebSocket tests, logs, etc.
2. **Identify which layers succeed vs. fail**: network layer (ping), transport layer (nc), application layer (curl/WebSocket), proxy/middleware (sidecar).
3. **Form a hypothesis**: Pinpoint the exact layer where the failure occurs.
4. **Pivot strategy based on hypothesis**: If the robot itself accepts direct connections but a sidecar/proxy fails, investigate the sidecar configuration—not the robot.

**Example:**
- Ping ✓, nc port ✓, direct WebSocket ✓ → Robot is fine.
- Sidecar logs show "falling back to mock mode" → Sidecar WebSocket handling is the problem.
- Action: Check sidecar WebSocket client code, not robot connectivity.

**Anti-pattern:** Running "try again" without analyzing why direct connection succeeded but sidecar failed.
