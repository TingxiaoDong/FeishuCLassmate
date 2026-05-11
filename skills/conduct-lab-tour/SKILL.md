---
name: conduct-lab-tour
description: |
  **路由入口** — 实验室参观全链路拆分为两段 skill,避免单文件过长:
  **准备讲解稿** → `lab-tour-prepare`; **现场 Temi 带览** → `lab-tour-run`。

  触发词:「带参观」「导览」「tour」「来人了」「有访客」「参观开始」。
  若用户明确「提前写稿/生成文档」→ **lab-tour-prepare**;
  若「人已到现场/机器人开始讲」→ **lab-tour-run**(可附带 doc 链接)。
---

# 导览入口

1. 判断意图属于 **准备期** 还是 **执行期**,调用对应 skill 名称引导 Agent。
2. 无定制 Doc 且需立即讲解时,直接按 **lab-tour-run**:它会退回通用剧本(数据来自 `data_layout` + `publicProjects` + `labInfo.specialAreas`)。
3. Temi 不可用 → **lab-tour-run** 中的纯文字降级(飞书输出)。

详细步骤见:

- [lab-tour-prepare/SKILL.md](../lab-tour-prepare/SKILL.md)
- [lab-tour-run/SKILL.md](../lab-tour-run/SKILL.md)
