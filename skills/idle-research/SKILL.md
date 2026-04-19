---
name: idle-research
description: |
  在 idle 窗口自主研究一个与实验室课题相关的话题,产出周报:本周关注主题 +
  相关工作 + 潜在启发。写入 Research 多维表 + 生成一篇飞书 Doc。

  **触发**: cron service `idle-loop` 自动触发;或用户显式说"做一次自主研究"。
---

# 闲时研究 Skill

## 前置

```
feishu_classmate_data_layout()
```

拿 `tables.projects.table_id` 和 `tables.research.table_id`。

---

## 步骤

### 1. 决定本周主题

- `feishu_bitable_app_table_record({ action: "list", table_id: <projects>, field_names: ["keywords","title","visibility"] })`
- 汇总所有 keywords,频次排序
- 查最近 2 周 Research 已写过的主题,避免重复:
  ```
  feishu_bitable_app_table_record({ action:"list", table_id:<research>, 
    filter: "CurrentValue.[created_at]>" + (Date.now() - 14*86400_000) })
  ```
- 选一个热门但最近没研究过的关键词作为本周主题

### 2. 搜索相关工作

用我们的专用 tool(不是 lark 的):
```
feishu_classmate_research_search_works({ topic: "<本周主题>", limit: 5 })
→ { works: [{title, url, abstract, year}, ...] }
```

该 tool 直接访问 arxiv.org 的公开 API,不需要授权。

### 3. LLM 综合生成启发

读 3–5 篇 abstract,产出:
- 1 句话共通观察
- 3 条对 lab 项目可能有用的启发,每条点名相关的 `project_id`

### 4. 写 Research 表

```
feishu_bitable_app_table_record({
  action: "create",
  app_token, table_id: <research>,
  fields: {
    report_id: "rep_<timestamp>_<rand>",
    week: "<2026-W16 样式>",
    topic: "<主题>",
    related_works: "<markdown 格式的工作清单>",
    insights: "<3 条启发>",
    source_projects: "<逗号分隔的 project_id>",
    created_at: Date.now()
  }
})
```

### 5. 写【研究报告】Doc

```
feishu_update_doc({ document_id: <cfg.docs.researchReports>, blocks: [...] })
```

在文档末尾追加这篇周报的完整 markdown。

### 6. 广播群推送摘要

`labInfo.broadcastChatId` 群里发一条带 Doc 链接的简短消息。

---

## 约束

- **不能**写 Projects 或 Gantt 表,只能读
- **不能**搜索与 lab 完全无关的话题
- 单次运行 ≤ 5 分钟(超时就把已收集的发出)
- 如果 3 步结果长度 < 200 字 → 不写 Research 表,只写【日常记录】Doc
