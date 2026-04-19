---
name: pivot-to-successful-diagnostic-as-new-baseline
description: Use when a diagnostic method succeeds where the primary method failed. Switch to the successful method as the new working baseline.
category: robotics/execution
---

## Pivot to Successful Diagnostic as New Baseline

1. When a diagnostic succeeds (e.g., direct WebSocket connects), note this as the **working baseline**.
2. The failure is now isolated to whatever the successful method bypasses (e.g., sidecar, proxy, auth layer).
3. Stop retrying the failing method. Instead, investigate the difference between the successful and failing approaches.
4. Report to the user: "Direct connection works, so the robot is reachable. The issue is specific to [sidecar/proxy]." 

**Example:**
- Sidecar + WebSocket → fails, falls back to mock.
- Direct Python WebSocket → succeeds.
- Pivot: Debug sidecar WebSocket client code, not robot connectivity.

**Anti-pattern:** Saying "let's try sidecar again" after discovering direct connection works, without investigating why the discrepancy exists.
