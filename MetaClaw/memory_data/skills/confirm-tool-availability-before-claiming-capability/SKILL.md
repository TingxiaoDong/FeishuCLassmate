---
name: confirm-tool-availability-before-claiming-capability
description: When asked if a capability exists (e.g., controlling a robot), verify actual tool/skill availability before responding.
category: agentic
---

## Confirm Tool Availability Before Claiming Capability

1. When user asks "Can you do X?" (e.g., "控制temi机器人"), do NOT immediately claim capability.
2. Search for existing tools, skills, or integrations that fulfill the requested function.
3. If no tool is found, respond honestly: "I don't currently have a tool/skill configured to do that. I can help you set one up."
4. If a tool IS found, confirm which specific tool and what parameters it requires.
5. Never assume a configuration entry (like IP/port) means a functional tool exists.

**Example:**
User: "你会操控temi机器人吗"
Correct response: "让我检查一下是否有可用的temi控制工具。" (then actually check)
Wrong response: "会！TOOLS.md里已经配了temi信息" (assumes config = capability)

**Anti-pattern:** Claiming "I can do X" based solely on configuration files without verifying a functional tool or skill exists.
