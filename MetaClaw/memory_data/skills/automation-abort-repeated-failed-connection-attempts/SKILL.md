---
name: automation-abort-repeated-failed-connection-attempts
description: Use after confirming a system is in mock/simulation mode. Stop attempting real connections and either resolve the issue or ask the user for help.
category: automation
---

## Stop Retrying After Mock Mode Confirmation

Once you have confirmed the system is running in mock mode:

1. Do NOT continue polling or re-attempting real connections.
2. Do NOT send additional diagnostic commands like `curl` or `sleep && curl` loops.
3. Acknowledge the state change: "The system is now in mock mode."
4. Either:
   - Ask the user to provide the correct robot IP or network details
   - Wait for the user to confirm the robot is ready before retrying

**Example:**
- Bad: `sleep 3 && curl -s http://localhost:8091/` (repeatedly)
- Good: "I cannot reach the robot. Please check that temi is powered on and on the same network, then provide the updated IP address."

**Anti-pattern:** Issuing repeated connection probes after mock mode has been confirmed.
