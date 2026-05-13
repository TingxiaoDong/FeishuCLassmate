---
name: weekly-digest
description: |
  每周五汇总实验室本周进展,产出 markdown doc + bitable 一行 + 群内广播。
  所有 bitable / doc 操作走 @larksuite/openclaw-lark 原生工具
  (`feishu_bitable_app_table_record`, `feishu_create_doc`, `feishu_update_doc`)。
  本 skill 只负责:数据聚合 → LLM 汇总 → 多通道落地。

  **触发词**: "来个周报"、"这周大家做了啥"、"周报"、"weekly digest"、
  以及未来的 cron(每周五 17:00,尚未实装,这里只记录契约)。
---

# 周报自动化 Skill

## 前置:拿数据布局

```
feishu_classmate_data_layout()
  → { app_token, tables: { projects, gantt, equipment, research,
                           weekly_digests, submissions, ... },
      docs: { publicProjects, privateProjects, researchReports, dailyLogs },
      labInfo: { name, broadcastChatId, ... } }
```

## 枚举值(严格)

| 字段 | 有效值 |
|---|---|
| Gantt.status | `未开始`、`进行中`、`完成`、`逾期` |
| Projects.status | `规划中`、`进行中`、`完成`、`搁置` |

`week` 字段格式固定为 `YYYY-Www`(例 `2026-W16`,ISO 8601 周号)。

---

## 数据收集流程(agent 编排)

设 `now = Date.now()`、`weekAgo = now - 7*86400_000`。

### 1. Gantt 本周状态变化

```
feishu_bitable_app_table_record({
  action: "list",
  app_token, table_id: <tables.gantt.table_id>,
  filter: "CurrentValue.[updated_at]>=" + weekAgo   // 如表无 updated_at 则用 due_date
})
```

按 `owner_open_id` 分组,统计每人:
- 本周 `status=完成` 的 milestone 数
- 本周 `progress` 变化 ≥ 20 的节点
- 当前 `status=逾期` 的节点(警告类)

### 2. 新项目

```
feishu_bitable_app_table_record({
  action: "list",
  app_token, table_id: <tables.projects.table_id>,
  filter: "CurrentValue.[created_at]>=" + weekAgo
})
```

### 3. 本周新增论文 (可选)

若 `tables.papers` 存在则:
```
filter: "CurrentValue.[added_at]>=" + weekAgo
```
不存在就跳过,不报错。

### 4. LLM 汇总成 markdown

Agent 自己把以上三部分拼成 markdown:标题 `# 📊 实验室周报 YYYY-Www`,然后四节:`## 本周完成的里程碑`、`## 新开项目`、`## 新增论文`、`## 需关注的逾期`。每项一行,以 `- **学生名** · <title/milestone>` 开头。

---

## 落地三通道

### 通道 1:写 Doc

用 `drive:drive` 查 `docs.researchReports` 所指 folder token(若配置是 Doc URL 就取其 parent folder;mock 模式下直接用它)。

```
feishu_create_doc({
  title: "周报 2026-W16",
  folder_token: <researchReports folder token>,
  content_md: <上面拼好的 markdown>
})
  → { doc_token, url }
```

### 通道 2:写 WeeklyDigests 行

```
feishu_bitable_app_table_record({
  action: "create",
  app_token, table_id: <tables.weekly_digests.table_id>,
  fields: {
    digest_id: "wd_<timestamp>_<rand>",
    week: "2026-W16",
    doc_token: "<上面返回的 url>",
    summary_md: "<markdown 全文,截断到 50000 字符>",
    completed_milestones: <数字>,
    active_projects: <数字>,
    published_papers: <数字>,
    created_at: <Date.now()>
  }
})
```

### 通道 3:群内广播

把 markdown 裁剪成 300 字以内的摘要 + Doc 链接,发到 `labInfo.broadcastChatId`:

```
feishu_im_bot_image 或纯文本消息 → chat_id=<broadcastChatId>
内容: "📊 本周周报:完成 N 个 milestone / M 个新项目 / K 篇论文。全文 👉 <url>"
```

---

## 场景:即席触发

用户说 `来个周报`:
1. 直接跑"数据收集流程"+"落地三通道"
2. 如果是周中,week 字段仍用当前 ISO 周号,`notes` 里写 "即席生成"

## 场景:cron(占位,未实装)

未来 cron `weekly-digest-cron` 在每周五 17:00 触发同样流程。当前代码里不实现,只在此文档说明契约:
- 上游传 `trigger: "cron"` 到 agent
- agent 跳过所有交互式确认,直接执行三通道

---

## 失败降级

- `docs.researchReports` 未配置 → 跳过通道 1,在 WeeklyDigests 的 `doc_token` 写空串,群里广播加一句"未配置 Doc folder"
- `feishu_create_doc` 返回 `99991672`(缺权限) → 跳过通道 1,继续通道 2+3
- Gantt / Projects 查询结果为 0 条 → 仍然落库一行,`summary_md` 写 "本周无更新"
- `labInfo.broadcastChatId` 为空 → 跳过通道 3,仅 Doc + Bitable 落地
- `data_layout` 返回 `app_token` 空 → 告知用户"数据库未初始化,请联系管理员跑 `openclaw classmate setup-bitable`",停止
