---
name: academic-paper-search
description: |
## 何时读取子文档

按需展开（避免一次塞满上下文）：

| 主题 | 文件 |
|------|------|
| 角色、核心目标 | [references/role-and-goals.md](references/role-and-goals.md) |
| 可信来源与应避开的站点 | [references/scholarly-sources.md](references/scholarly-sources.md) |
| 意图分析 + 构造多组学术 Query | [references/intent-and-queries.md](references/intent-and-queries.md) |
| 检索策略 + 迭代改进 | [references/search-and-iteration.md](references/search-and-iteration.md) |
| 论文评估、排序、引用扩展、输出模板、行为约束、高阶行为与检索哲学 | [references/evaluation-output-rules.md](references/evaluation-output-rules.md) |

## 执行流程（总览）

执行任何检索任务时，按顺序落实下列步骤；细节与原文约束见上表链接。

1. **理解意图** — 抽取主题、领域、问题、技术词、约束、期望论文类型；请求模糊则推断方向。
2. **生成多组 Query** — 基础词、学术表述、高被引/综述向、最新研究向、同义词扩展（见 `intent-and-queries.md`）。
3. **分阶段检索** — 先宽后窄；依据高相关文献、重复关键词、重要作者、**引用关系**、常见方法迭代收紧（见 `search-and-iteration.md`）。
4. **评估** — 相关性、质量（引用、venue、时效、方法严谨性）、论文类型归类。
5. **排序** — 优先高相关、有学术影响、严谨、在合适场景下兼顾新近；避免仅关键词表面匹配。
6. **引用扩展** — 对核心论文：参考文献、cited-by、奠基工作、后续跟进，形成研究谱系。
7. **结构化输出** — 每篇：title / authors / year / venue / paper type / 相关性说明；再归纳主题、方法、趋势与可能空白（见 `evaluation-output-rules.md`）。
8. **迭代** — 结果弱则改 Query、扩/缩范围、换平台、换邻近领域，直到相关性改善。

## 硬性约束（摘要）

- **必须**：分步思考；检索前推理；优先一手学术源；**以摘要为主**评估，不单看标题；不捏造文献信息。
- **禁止**：伪造引用或推荐虚假论文；轻信低质站；仅凭关键词重叠堆砌无关论文。

完整「必须 / 禁止」、输出字段模板与高级行为见 [references/evaluation-output-rules.md](references/evaluation-output-rules.md)。
