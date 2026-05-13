---
name: manage-gantt
description: |
  当学生需要新建项目、更新项目进度、或回复每日节点提醒时使用。
  所有数据操作走 @larksuite/openclaw-lark 的原生 `feishu_bitable_app_table_record`,
  本 skill 只负责流程编排和人机交互(确认卡 / 话术)。

  **触发词**: "建项目"、"新建 project"、"帮我建个甘特图"、"项目进度"、
  "today 我完成了 …"、"进度 XX%"、"milestone 达成"、回复系统发出的节点提醒。
---

# 进度管理 Skill

## 前置:总是先拿数据布局

```
feishu_classmate_data_layout()
  → { app_token, tables: { projects, gantt, equipment, research } }
```

下面所有 bitable 操作都直接用返回的 `app_token` + `tables[x].table_id` 丢给 lark 的原生工具。

---

## 场景 A:学生新建项目(项目 → 甘特图)

### 步骤

1. 解析学生口述/上传的项目描述,抽出结构化草稿:
   ```
   {
     title: "...",
     keywords: ["...","..."],
     visibility: "可公开" | "保密",
     abstract: "...",
     milestones: [{ milestone: "...", due_date_iso: "YYYY-MM-DD" }, ...]
   }
   ```
   用 LLM 自己能力做,不调 tool。

2. 用飞书交互卡展示给学生确认(用 `feishu_ask_user_question` 或直接文字):
   - 标题、关键词、可见性、摘要
   - 3–5 个 milestone + 对应日期

3. 学生确认后:

   **3a 写 Projects 表**
   ```
   feishu_bitable_app_table_record({
     action: "create",
     app_token: <layout.app_token>,
     table_id: <layout.tables.projects.table_id>,
     fields: {
       project_id: "proj_<timestamp>_<rand>",
       title: "<title>",
       owner_open_id: [{ id: "<学生 open_id>" }],
       keywords: ["...","..."],
       visibility: "可公开",     // 必须严格用 可公开 / 保密 之一
       status: "规划中",          // 必须严格用 规划中 / 进行中 / 完成 / 搁置 之一
       created_at: <Date.now()>,  // 毫秒时间戳
       updated_at: <Date.now()>
     }
   })
   ```

   **3b 批量写 Gantt 节点**
   ```
   feishu_bitable_app_table_record({
     action: "batch_create",
     app_token: <layout.app_token>,
     table_id: <layout.tables.gantt.table_id>,
     records: [
       {
         fields: {
           gantt_id: "g_<timestamp>_<rand>",
           project_id: "<同上 project_id>",
           owner_open_id: [{ id: "..." }],
           milestone: "<节点名>",
           due_date: <该日期的毫秒时间戳>,
           progress: 0,
           status: "未开始"
         }
       },
       ...
     ]
   })
   ```

   **3c(可选) 写项目摘要到飞书 Doc**
   - `可公开` → 追加到 `docs.publicProjects` Doc (用 `feishu_update_doc`)
   - `保密` → 追加到 `docs.privateProjects` Doc

### 枚举值强约束

| 字段 | 有效值 |
|---|---|
| visibility | `可公开`、`保密` |
| status (Projects) | `规划中`、`进行中`、`完成`、`搁置` |
| status (Gantt) | `未开始`、`进行中`、`完成`、`逾期` |

**Agent 必须严格用以上中文值**。写错会报 `FieldConvFail` 错误(code 125406X)。

---

## 场景 B:回复每日节点提醒

系统每天 09:00 会通过 `feishu_classmate` 的 cron 给学生发消息:

```
📅 今天是【{milestone}】的计划完成日。
项目: {project_id}
请回复进度 (0-100)、当前状态和卡点...
(gantt_id=g_xxx)
```

### 步骤

1. 从学生回复解析 `progress_pct` 和 `notes`(LLM 处理)
2. 更新 Gantt 行:
   ```
   feishu_bitable_app_table_record({
     action: "update",
     app_token: <layout.app_token>,
     table_id: <layout.tables.gantt.table_id>,
     record_id: <找到该 gantt_id 对应的 record_id>,
     fields: {
       progress: <0-100>,
       status: <根据 progress 推断>,
       notes: "<学生回复摘要>"
     }
   })
   ```
   - 找 record_id: 先 `action: "list"` + `filter: "CurrentValue.[gantt_id]=\"g_xxx\""`
3. 回复学生: "已更新,加油 💪"

---

## 场景 C:查询学生的所有项目/进度

1. `feishu_classmate_data_layout` 拿 table_id
2. `feishu_bitable_app_table_record({ action: "list", filter: "CurrentValue.[owner_open_id]=[{\"id\":\"ou_xxx\"}]" })`
3. 格式化输出(进度 bar + 最近 notes + 逾期标红)

---

## 失败处理

- lark 返回 `code 99991672` (缺 scope) → 告诉学生"权限不足,请 admin 联系",停止流程
- lark 返回 `code 1254xxx` (字段类型错) → LLM 自查上面的枚举值表,用正确值重试一次
- `data_layout` 返回 `app_token` 为空 → 告诉学生"数据库未初始化,请联系管理员跑 `openclaw classmate setup-bitable`"
