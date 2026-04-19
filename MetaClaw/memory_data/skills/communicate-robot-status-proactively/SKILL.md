---
name: communicate-robot-status-proactively
description: Use when interacting with a robot via sidecar or WebSocket. Always communicate status changes and errors to the user instead of returning NO_REPLY.
category: communication
---

## Proactive Robot Status Communication

1. **On command success**: Report briefly: "✅ Temi 已开始移动前往入口。"
2. **On command failure**: Always explain what happened: "❌ 移动失败：WebSocket 连接已断开 (1001)。正在尝试重新连接..."
3. **On async completion**: Don't return `NO_REPLY`. Summarize the result if relevant to the user's request.
4. **On repeated failures**: After 2 failed attempts, ask the user for next steps instead of continuing to retry.

**Example response to WebSocket error:**

检测到连接错误 (1001 going away)。这表示 Temi 端关闭了连接。
正在检查 sidecar 状态...
如果持续失败，可能需要重启 temi-sidecar 服务。


**Anti-pattern:** Silently returning `NO_REPLY` or only sending technical curl output without explaining the meaning to the user.
