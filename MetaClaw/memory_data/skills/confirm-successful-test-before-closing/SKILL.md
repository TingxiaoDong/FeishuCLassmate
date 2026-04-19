---
name: confirm-successful-test-before-closing
description: Use after receiving test output to explicitly confirm success criteria are met and communicate a clear pass/fail status to avoid ambiguity.
category: robotics/execution
---

## Confirm Successful Test Before Closing

1. **Parse test output** for explicit success indicators (e.g., `"status":"ok"`, `"ok":true`)
2. **Verify expected values** match: location name, mock mode, robot response
3. **State outcome explicitly**: "✅ Test PASSED: Temi received correct location"
4. **If partial success**, report what worked vs. what still needs investigation
5. **End with next action** or confirmation that task is complete

python
# Verify these fields in response:
assert response["status"] == "ok"
assert response["mock"] == False  # Real robot, not mock
assert "Entrance" in response["message"]


**Anti-pattern:** Reporting test results vaguely ("it seems to work") without verifying specific success criteria.
