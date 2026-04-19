---
name: communicate-system-error-fallbacks-to-user
description: When system messages indicate fallback behavior (e.g., mock mode activation), explicitly inform the user rather than treating it as routine.
category: robotics/execution
---

## Communicate Fallback Behavior to Users

When system messages indicate automatic fallback behavior:

1. **Detect fallback signals**: "falling back to mock mode", "using mock", "mock: true"
2. **Immediately inform the user** that the operation did NOT run on real hardware
3. **Explain implications**: mock mode means commands are simulated, not executed
4. **Ask for confirmation** to proceed in mock mode or retry with real hardware

**Example response:**

⚠️ 检测到系统已自动切换到 mock 模式。

这意味着刚才的导航指令是模拟执行，真实 Temi 不会移动。

如需真实执行，请确保机器人连接正常后重新发起请求。


**Anti-pattern:** Silently proceeding when mock mode activates, allowing the user to believe the real robot received the command.
