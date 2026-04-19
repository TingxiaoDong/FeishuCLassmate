---
name: robotics-execution-verify-navigation-completion
description: Use when sending navigation commands to a robot. Always verify the robot actually reached the destination by checking position or arrival status, not just command acknowledgment.
category: robotics/execution
---

## Verify Robot Navigation Completion

1. After sending a goto command, DO NOT assume success from acknowledgment alone.
2. Poll the robot's position endpoint until it matches the destination coordinates OR the status indicates arrival.
3. Check for specific "arrived" or "completed" events in the robot's response stream.
4. Compare initial position with final position to confirm movement occurred.
5. If position remains unchanged after command, the navigation failed.

**Anti-pattern:** Sending a goto command and immediately returning success based on command acknowledgment alone. The robot may have rejected the command or failed to start moving.
