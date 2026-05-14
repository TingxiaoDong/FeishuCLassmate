# 二、研究计划制定

## 2.1 研究计划结构（定题后必须能产出）

对选定（或用户给定）课题，生成下列章节（建议写入飞书 Doc，便于评审与版本历史）：

```text
Research Goal
Background
Problem Definition
Hypothesis
Technical Route
Milestones
Risk Analysis
Expected Outcome
Paper Target
Demo Target
```

## 2.2 任务拆解维度

将工作拆入可执行工作包（不必一次填满，可按两周迭代增量）：

| 阶段 | 包含内容 |
|------|----------|
| Literature Review | 论文调研、baseline、benchmark 列表 |
| System Design | 架构、模块、API / Agent 编排 |
| Implementation | 前端、后端、模型、数据、Agent 实现 |
| Experiment | 指标、ablation、（如适用）user study 设计 |
| Visualization | demo、UI、行为回放与叙事 |
| Writing | paper / slides / poster 大纲与时间窗 |

每个工作包应带：**负责人（或待定）**、**依赖**、**粗估工期**、**风险**，供写入 Gantt 表（见 `feishu-gantt-lark.md`）。

## 2.3 与甘特的衔接

计划定稿后，**同一套 Milestones** 应映射为 `gantt`（或项目约定表）中的多行记录：任务名、起止、状态、依赖、owner；再配置时间线视图（见 `feishu-gantt-lark.md`）。
