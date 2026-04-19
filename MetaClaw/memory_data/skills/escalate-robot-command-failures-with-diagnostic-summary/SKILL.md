---
name: escalate-robot-command-failures-with-diagnostic-summary
description: Use when robot command retries have been exhausted. Present a clear diagnostic summary to the user and suggest next steps rather than continuing to retry.
category: robotics/execution
---

## Escalate Robot Failures with Diagnostic Summary

After exhausting retries or detecting persistent failures:

1. **Stop retrying** the same failing command.
2. **Compile a diagnostic summary** including:
   - Command attempted
   - Error received (verbatim)
   - Number of attempts made
   - Robot state at time of failure (if `/status` responded)
3. **Present findings to the user** with clear next steps.
4. **Offer alternatives** when possible: "Goto command unavailable. You may try manual control or restart the robot service."

**Example escalation message:**
> Robot navigation command to "入口" failed 3 times with WebSocket error 1001 (going away). The API server at port 8091 responded to health checks, but the robot's WebSocket connection keeps dropping. Possible causes: robot network issue, service timeout misconfiguration, or robot firmware problem. Please check the robot's Wi-Fi connection or restart the robot service.

**Anti-pattern:** Saying "trying again" without user notification when the underlying issue persists, or continuing to retry after clear evidence of a persistent problem.
