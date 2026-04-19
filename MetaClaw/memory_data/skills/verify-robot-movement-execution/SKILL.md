---
name: verify-robot-movement-execution
description: Use after sending any movement command to a robot. Always verify that is_moving becomes true or poll for position change to confirm execution.
category: robotics/execution
---

## Verify Robot Movement Execution

1. **Immediate check**: After POSTing a goto command, check that the response indicates success (`ok: true`).
2. **Poll for transition**: Within 3-5 seconds, query `/status` and confirm `is_moving: true`.
3. **Wait for completion**: If `is_moving: true`, poll until `is_moving: false` (arrived) or until a timeout (15s).
4. **Confirm arrival**: If the robot arrived, verify position is near the target location.
5. **On timeout**: If robot never starts moving, the command was rejected — report this as a failure.

**Example verification loop:**
bash
# Issue command
curl -s -X POST http://localhost:8091/goto -d '{"location": "入口"}'

# Poll with timeout
for i in {1..10}; do
  status=$(curl -s http://localhost:8091/status | jq -r '.is_moving')
  [ "$status" = "true" ] && echo "Robot started moving" && break
  sleep 1
done


**Anti-pattern:** Sending a goto command and assuming success without polling `is_moving` or checking the response.
