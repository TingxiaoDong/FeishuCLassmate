---
name: robotics-execution-diagnose-no-movement
description: Use when a robot acknowledges a navigation command but does not move. Follow systematic diagnostics before assuming location name issues.
category: robotics/execution
---

## Diagnose Robot No-Movement Failure

1. DO NOT immediately assume the location name is wrong.
2. First verify basic connectivity: send a simple command like `status` or `info` to confirm robot is responsive.
3. Check if the robot is in an error state or has an obstruction via status endpoint.
4. Try sending a different command type (e.g., `move` with small distance) to test if the robot can execute ANY command.
5. If the robot responds to status but not navigation, THEN check if the location name exists in the robot's map.
6. Document what diagnostics were tried before concluding the cause.

**Anti-pattern:** Jumping to conclusions about wrong location names without first verifying the robot can execute any movement command. This wastes time investigating the wrong issue.
