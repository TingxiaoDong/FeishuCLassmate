---
name: dyn-001
description: Use when a robot connection fails and the system falls back to mock/simulation mode. Clearly communicate the connection failure to the user with actionable next steps.
category: robotics/execution
---

## Report Robot Connection Failure Clearly

When a robot cannot be reached and the system falls back to mock mode:

1. State the connection status directly: "Cannot reach the robot at [IP]. The system is now running in mock/simulation mode."
2. Explain the impact: "Commands will be simulated but will NOT execute on the physical robot."
3. Ask the user for help with ONE specific action:
   - "Please verify the robot is powered on and connected to the network."
   - "Check if the robot's IP address has changed."
   - "Confirm your computer is on the same network as the robot."
4. Wait for user confirmation before retrying connections.

**Anti-pattern:** Continuing to send diagnostic commands or testing the real connection repeatedly without telling the user that mock mode is active.
