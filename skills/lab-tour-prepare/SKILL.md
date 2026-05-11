---
name: lab-tour-prepare
description: |
  教师/管理员为来访访客「预生成」个性化导览讲解稿时使用。
  读取知识库中的导览母版,结合访客单位与日期,新建一篇飞书 Doc 作为当次剧本。
  **触发**: 「给 XX 单位准备导览」「生成今天的参观讲解稿」「预生成导览文档」。

  **不要用于**: 访客已到现场的边走边讲 —— 请用 skill `lab-tour-run`。
---

# 导览 · 准备期

## 最短路径

1. `feishu_classmate_data_layout()` → 取 `plugin_docs.tourTemplate`(母版)与 `plugin_docs.publicProjects`。
2. 若无 `tourTemplate`,向用户说明需在插件配置 `docs.tourTemplate` 或环境变量 `FEISHU_DOC_TOUR_TEMPLATE` 中配置母版 Doc,或用户提供母版链接/token。
3. 用 **openclaw-lark** 的 `feishu_fetch_doc` / `feishu_search_doc_wiki` 读母版全文。
4. 按用户给的访客信息,用 LLM 生成结构化 Markdown(章节必须与 [**doc-format**](./references/doc-format.md) 一致)。
5. **openclaw-lark** `feishu_create_doc`(或等价) 新建 Doc,标题建议:`{日期}-{访客简称}-导览`。
6. 回复用户:**新 Doc 链接**、建议的**现场唤醒句**(写入 doc 末尾「唤醒」一节),并提示执行现场导览时调用 skill **`lab-tour-run`** 并传入该 `document_id`/链接。

## 详细步骤与占位符

见 [references/prepare-detail.md](./references/prepare-detail.md)。

## 降级

- 母版读失败 → 仅用 `labInfo` + `publicProjects` 摘要生成短篇 Doc,仍保存为新文档。
