---
name: verify-robot-navigation-completion-before-reporting-success
description: After sending a navigation command to the robot, verify the robot has arrived at the destination before confirming success to the user.
category: robotics/execution
---

## Verify Robot Navigation Completion

After sending a `/goto` or navigation command:

1. **Wait and poll** the `/status` endpoint until `is_moving: false`
2. **Check position** matches the expected destination coordinates
3. **Confirm arrival** only after movement stops and position is correct

**Example workflow:**
bash
# Send navigation command
curl -X POST "http://localhost:8091/goto" -d '{"location":"入口"}'

# Poll status until movement stops
curl "http://localhost:8091/status"
# Repeat until: {"is_moving": false, "position": {...}}

# Only then report to user
"Temi 已到达入口 ✅"


**Anti-pattern:** Reporting "命令已送达，会自己走过去" immediately after sending the command, without confirming actual arrival.
