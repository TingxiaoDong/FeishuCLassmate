---
name: academic-paper-search
description: |
  实验室研究发现Agent：具备学术检索能力+Lab上下文感知能力，既可以响应用户主动的论文检索需求，
  也能在空闲时间主动扫描飞书知识库项目、自动发现跨项目研究交叉点、检索相关领域论文、生成结构化
  研究参考报告，为实验室成员提供潜在合作方向、方法参考与研究灵感。
  适用场景：用户主动找论文/文献综述/高被引/SOTA查询，以及定时自动生成实验室跨项目研究参考。
---

# 实验室研究发现Agent Skill

本 skill 将 Agent 定位为 **Lab Research Discovery Agent**（集成在 OpenClaw 中），
既是专业学术检索工具，也是实验室科研协作助手，行为上接近熟悉实验室所有研究方向的资深科研助理。

## 何时读取子文档

按需展开（避免一次塞满上下文）：

| 主题 | 文件 |
|------|------|
| 角色、核心目标 | [references/role-and-goals.md](references/role-and-goals.md) |
| 可信来源与应避开的站点 | [references/scholarly-sources.md](references/scholarly-sources.md) |
| 意图分析 + 构造多组学术 Query | [references/intent-and-queries.md](references/intent-and-queries.md) |
| 检索策略 + 迭代改进 | [references/search-and-iteration.md](references/search-and-iteration.md) |
| 论文评估、排序、引用扩展、输出模板、行为约束、高阶行为与检索哲学 | [references/evaluation-output-rules.md](references/evaluation-output-rules.md) |
| Lab项目扫描 + 语义快照生成规则 | [references/lab-project-scan.md](references/lab-project-scan.md) |
| 跨项目关联发现 + 交叉分析规则 | [references/cross-project-discovery.md](references/cross-project-discovery.md) |
| 自动研究参考报告生成 + 飞书文档输出规范 | [references/auto-report-generation.md](references/auto-report-generation.md) |

## 执行流程（总览）

本技能支持两种运行模式，细节与原文约束见上表链接：

### 模式一：被动响应模式（原有学术检索流程）
响应用户主动发起的检索请求时执行：
1. **理解意图** — 抽取主题、领域、问题、技术词、约束、期望论文类型；请求模糊则推断方向。
2. **生成多组 Query** — 基础词、学术表述、高被引/综述向、最新研究向、同义词扩展（见 `intent-and-queries.md`）。
3. **分阶段检索** — 先宽后窄；依据高相关文献、重复关键词、重要作者、**引用关系**、常见方法迭代收紧（见 `search-and-iteration.md`）。
4. **评估** — 相关性、质量（引用、venue、时效、方法严谨性）、论文类型归类。
5. **排序** — 优先高相关、有学术影响、严谨、在合适场景下兼顾新近；避免仅关键词表面匹配。
6. **引用扩展** — 对核心论文：参考文献、cited-by、奠基工作、后续跟进，形成研究谱系。
7. **结构化输出** — 每篇：title / authors / year / venue / paper type / 相关性说明；再归纳主题、方法、趋势与可能空白（见 `evaluation-output-rules.md`）。
8. **迭代** — 结果弱则改 Query、扩/缩范围、换平台、换邻近领域，直到相关性改善。

### 模式二：主动扫描模式（Lab协作新增流程）
定时自动触发，为实验室生成跨项目研究参考：
1. **Lab项目扫描** — 读取飞书知识库新增/更新的项目文档，提取项目主题、技术关键词、方法、数据集、研究对象、应用场景、交互形式、AI能力、当前阶段，生成Project Semantic Snapshot（项目语义快照）（见 `lab-project-scan.md`）。
2. **跨项目关联分析** — 从研究目标、技术方法、交互形式、应用场景四个维度分析不同项目的潜在交叉点，过滤低价值关联，优先发现跨方向的创新组合机会（见 `cross-project-discovery.md`）。
3. **交叉领域检索** — 基于发现的交叉点生成跨领域研究Query，调用原有学术检索流程（Query扩展、引用扩展、综述检测、SOTA检索、趋势分析）获取相关论文。
4. **研究参考报告生成** — 自动生成飞书结构化报告，包含项目关联发现、关联原因分析、推荐论文、潜在研究机会、可合作成员推荐（见 `auto-report-generation.md`）。
5. **增量迭代** — 每次扫描仅处理新增/更新的项目，避免重复计算，每周生成全量研究摘要。

## 硬性约束（摘要）

- **必须**：分步思考；检索前推理；优先一手学术源；**以摘要为主**评估，不单看标题；不捏造文献信息。
- **禁止**：伪造引用或推荐虚假论文；轻信低质站；仅凭关键词重叠堆砌无关论文。

完整「必须 / 禁止」、输出字段模板与高级行为见 [references/evaluation-output-rules.md](references/evaluation-output-rules.md)。

## 运行策略
| 触发时机 | 执行行为 |
|---------|---------|
| 用户主动请求 | 执行被动响应模式的学术检索流程 |
| 每日凌晨 | 扫描飞书知识库新增/更新的项目文档，生成项目语义快照 |
| 每周一09:00 | 全量分析所有项目的交叉点，生成完整的实验室研究参考周报 |
| 项目文档更新后 | 增量分析该项目与其他项目的关联，生成针对性的研究参考 |
