---
name: handle-async-execution-failure-with-user-notification
description: When an async command completes with a failure signal (SIGKILL, SIGTERM, or falling back to mock mode), always notify the user instead of returning NO_REPLY.
category: robotics/execution
---

## Handle Async Execution Failures Explicitly

When a system message reports an async command failure (e.g., "Exec failed", "SIGKILL", "falling back to mock mode"), you must:

1. **Parse the failure signal** from the system message
2. **Do NOT return NO_REPLY** - this leaves the user without feedback
3. **Acknowledge the failure** to the user clearly:
   - State what failed (e.g., "The robot command execution was killed")
   - Explain the consequence (e.g., "Falling back to mock mode")
   - Offer next steps or ask for guidance

**Example response:**

抱歉，机器人命令执行遇到了问题（进程被终止）。
目前处于 mock 模式，真实指令未送达。

建议：请检查机器人连接后重新发起请求。


**Anti-pattern:** Returning `NO_REPLY` when async execution fails, leaving the user unaware that their request was not completed.
