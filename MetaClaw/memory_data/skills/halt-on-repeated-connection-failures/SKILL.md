---
name: halt-on-repeated-connection-failures
description: Use when the same connection attempt fails 3+ times consecutively, to stop and report the persistent failure to the user instead of continuing retry attempts.
category: robotics/execution
---

## Halt on Repeated Connection Failures

When attempting to connect to a robot or service:

1. **Track failure count**: If the same connection method fails 3 times in a row, stop retrying.

2. **Patterns that indicate a stop condition**:
   - Same error message repeated: `"going away"`, `"404 WebSocket Upgrade Failure"`
   - Same command timeout: `Command timed out after 5 seconds`
   - Same response: `<html>404...`

3. **After 3 failures, do this instead**:
   - Report to the user what you've tried and what failed
   - Ask for clarification on the correct connection method
   - Suggest checking the robot's documentation or configuration

4. **Example stopping response**:
   
   I've tried multiple connection attempts to 192.168.31.121:8175:
   - HTTP POST with WebSocket headers: failed
   - curl API requests: returned 404
   - Port connectivity: confirmed (ping works)
   
   The robot endpoint doesn't appear to accept standard HTTP or WebSocket connections in the expected format. Could you verify the correct API endpoint or protocol for this robot?
   

**Anti-pattern:** Continuing to execute `find`, `ls`, `ps` commands after connection attempts fail, without addressing the root cause of the connection failure.
