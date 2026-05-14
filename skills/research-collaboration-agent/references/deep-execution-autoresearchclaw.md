# 深度执行：交接给 AutoResearchClaw（验证实验性 idea）

本 skill 负责 **0→1 规划**；真正「跑实验、验证 idea 成不成立」交给
**AutoResearchClaw（ARC）** —— 一个 23-stage 流水线（真实文献检索 + sandbox 实验
+ 多 agent peer review），产出 conference-ready 论文草稿作为**验证产物**。

ARC 通过本仓库的 `arc-sidecar/`（Python FastAPI shim）异步驱动，插件侧暴露三个工具：
`feishu_classmate_research_arc_start` / `_status` / `_fetch`。

## 何时交接

**全部满足**才交接，否则继续在本 skill 内规划：

1. 课题已定题，且研究计划成形 —— 至少有 `Research Goal` + `Technical Route` + `Hypothesis`
   （见 [research-planning.md](research-planning.md) §2.1）
2. 用户明确表达「想认真验证 / 跑实验 / 出篇论文」，不是还在脑暴阶段
3. 这是一个**可被实验验证**的 idea（有可操作的假设），不是纯综述类问题

不满足 → 留在本 skill：继续 `topic-discovery` / `research-planning`，或走
`autonomous-research`（每周轻量调研周报，不跑实验）。

## 交接流程

```
1. arc_start: 把 Research Goal 作为 topic 发起 run
   feishu_classmate_research_arc_start({
     topic: "<Research Goal,一句话课题>",
     mode: "auto",                 // 或 "co-pilot":关键节点要人工把关时
     hypothesis: "<要验证的明确假设>",
     plan_doc_url: "<研究计划所在飞书 Doc 链接>"
   })
   → 返回 run_id。立刻把 run_id 写进 research 多维表新建的一行(状态=running)。

2. arc_status: 有节制地轮询(run 是分钟~小时级,不要密集轮询)
   feishu_classmate_research_arc_status({ run_id })
   → status ∈ queued | running | completed | failed
   推荐:发起后告知用户「已交给 ARC 验证,完成会通知」,
   靠 ARC 侧 openclaw_bridge 的 use_message 推完成通知,而不是阻塞式死等。

3. arc_fetch: status=completed 后取交付物
   feishu_classmate_research_arc_fetch({ run_id })
   → files: paper_draft / paper_tex / references_bib / verification_report / reviews
     dirs:  charts / experiments / evolution / deliverables
```

## 结果回写（拿到交付物后必须做）

用 `@larksuite/openclaw-lark` 原生 Bitable / Doc 工具：

- **`research` 多维表**：更新该 run 那一行 —— 状态=completed、`run_id`、`hypothesis`、
  peer review 评分（从 `reviews` preview 提取）、结论（idea 是否被支持）、交付物 workdir 路径
- **飞书 Doc**：新建一篇，把 `paper_draft` 的 preview / 全文、`reviews` 摘要贴进去，
  命名如「ARC 验证报告 · <课题> · <日期>」，链接回填到 research 表行
- **失败时**（status=failed）：把 `error` + `log_tail` 写进 research 表行，标记 failed，
  并向发起人简述失败原因（常见：ARC 未安装 / LLM key 未配 / 实验 sandbox 失败）

## 交接之后

idea 一旦被 ARC 验证为「成立、值得推进」，项目就进入稳定执行管线 ——
**引导或交接到 `manage-project`**（立项、甘特、周报），不要在本 skill 里继续跟。

## mock 模式说明

`arc.mockMode`（默认 true）或 sidecar 的 `ARC_MOCK=1` 时，`_start` 会返回一个
模拟 run：~3s 后变 completed，交付物是占位内容。可用于在没装 ARC 时打通工具链路，
但**不要把 mock 结果当作真实验证结论**回写给用户。

## NEVER / ALWAYS

- **NEVER** 在 idea 还没成形（缺 Hypothesis / Technical Route）时就 `arc_start`
- **NEVER** 阻塞式高频轮询 `arc_status` —— run 很长，交给 `use_message` 通知
- **NEVER** 把 `mock=true` 的交付物当真实验证结果
- **ALWAYS** `arc_start` 后立即在 `research` 表落一行，run_id 不能只存在对话里
- **ALWAYS** 交付物回写飞书（表 + Doc）后再告知用户，保证可追溯
