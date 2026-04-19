---
name: robotics-direct-command-execution
description: When user requests a specific robot action (move, speak, stop), immediately invoke the corresponding function without reading documentation or searching for code first.
category: robotics/execution
---

## Execute Robot Commands Directly

When a user explicitly requests a robot action (e.g., "move temi to entrance", "speak", "stop"), execute the action immediately.

1. Identify the appropriate function from context:
   - Navigate: `feishu_classmate_temi_navigate_to({ location: "X" })`
   - Speak: `feishu_classmate_temi_speak({ text: "message" })`
   - Stop: `feishu_classmate_temi_stop({ immediate: true })`

2. Call the function with the user's requested parameters.

3. Do NOT read SKILL.md or other documentation first.

**Example:**
User: "请操控temi机器人移动到入口"
Response: Call `feishu_classmate_temi_navigate_to({ location: "入口" })`

**Anti-pattern:** Reading TOOLS.md or searching for .ts files before executing the known command.
