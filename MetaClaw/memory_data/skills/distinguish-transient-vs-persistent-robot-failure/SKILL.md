---
name: distinguish-transient-vs-persistent-robot-failure
description: Use when robot commands fail with identical errors across multiple attempts. Recognize when failures are persistent rather than transient network glitches.
category: robotics/execution
---

## Distinguish Transient from Persistent Robot Failures

Not all errors should be retried the same way:

1. **Transient indicators**: Single occurrence, no pattern, robot responds to `/status`.
2. **Persistent indicators**: Identical error repeated 2+ times, robot fails `/status` check, error message unchanged.

For **transient failures**:
- Retry once after a brief delay.
- Inform the user: "Temporary connection issue, retrying."

For **persistent failures**:
- Do NOT keep retrying the same command.
- Perform a full diagnostic check (robot state, service health, WebSocket handshake).
- Report to the user with specifics: "Robot command consistently failing — WebSocket disconnects at handshake."

python
# Track failure patterns
if failure_count >= 2 and error_signature == previous_error:
    # This is persistent — stop retrying, escalate
    report_user("Persistent failure detected. Manual intervention may be required.")


**Anti-pattern:** Treating every failure as a temporary glitch and retrying indefinitely, as seen when the assistant keeps calling `/goto` despite receiving identical 1001 errors.
