---
name: extract-reasonable-defaults-for-minimal-requests
description: When user provides minimal but actionable project/task requirements, use sensible defaults for missing details instead of asking excessive clarifying questions.
category: productivity
---

## Extract Reasonable Defaults for Minimal Requests

When user provides a task with minimal info (e.g., "create a project: RLHF 6 weeks divided into 3 phases"), use standard defaults:

1. **Start date**: Use today's date
2. **Phase names**: Use generic labels like "阶段1/阶段2/阶段3" or "Phase 1/2/3"
3. **Phase goals**: Copy user's description as overall goal, split evenly across phases
4. **Owner**: Use the sender's ID from message metadata
5. **Duration**: Calculate from start date per phase

**Example:**
- User input: "建个项目:RLHF 6周分3阶段"
- Assistant output: Create project with start=today, phases=[(Week1-2, RLHF基础), (Week3-4, RLHF进阶), (Week5-6, RLHF精调)]

6. **After creation**: Tell user "已创建，日期/负责人如有误请告知修改"

**Anti-pattern:** Asking 3+ clarifying questions before doing anything. One follow-up question max.
