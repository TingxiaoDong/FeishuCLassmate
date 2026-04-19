---
name: handle-contextual-date-messages-with-clarification
description: Use when user messages contain dates or timestamps with vague references like '4/18' or '阶段目标' without explicit instructions. Ask clarifying questions instead of guessing intent.
category: communication
---

## Clarify Intent on Contextual Date Messages

When a message contains date references (e.g., "4/18", "today") combined with ambiguous phrases like "阶段目标", "先空着", or "开始", do NOT assume what action to take.

**Steps:**
1. Pause and identify what is unclear: What does the user want to DO with this date?
2. Ask a direct question: "您是想...吗？" or "请问您希望我做什么？"
3. Wait for confirmation before executing any tool calls.
4. If multiple interpretations exist, list them and ask the user to choose.

**Example:**
User: "4/18，阶段目标先空着"
Wrong: "好的，4/18 开始！正在建档..."
Correct: "请问您是想在4/18这个日期做什么操作？是新建一个记录、查询某个项目状态，还是其他？"

**Anti-pattern:** Responding with action words like "建档", "开始", "创建" without explicit user confirmation.
