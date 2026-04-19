---
name: skip-exploration-for-known-operations
description: When the conversation already contains the function name or parameters needed for the requested task, use them directly instead of searching for them.
category: robotics/execution
---

## Use Available Function Info Without Re-searching

If the function name, parameters, or robot IP/port are already provided in the conversation context, use them immediately.

1. Scan the conversation for existing function references.
2. If `feishu_classmate_temi_*` functions or robot connection details (IP: 192.168.x.x) are visible, call the function directly.
3. Do NOT re-discover by running `grep`, `find`, or reading skill files.

**Example from context:**
User request: "移动到入口" with existing mention of `feishu_classmate_temi_navigate_to`
Action: Call the function immediately with the location parameter.

**Anti-pattern:** Running `grep -r "temi" --include="*.ts"` when temi functions are already documented in the conversation.
