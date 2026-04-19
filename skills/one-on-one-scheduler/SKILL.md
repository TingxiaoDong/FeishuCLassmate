---
name: one-on-one-scheduler
description: |
  导师与学生 1:1 会议的提议 → 预约 → 准备 → 复盘全流程。时间协商走
  `feishu_calendar_freebusy` + `feishu_calendar_event`,议程聚合 Gantt /
  Submissions / ToolTrace 再写 Doc,会后纪要回写 OneOnOnes 表。

  **触发词**: "约学生 1:1"、"schedule 1on1"、"下周见面谈"、"约 <学生> 聊聊"、
  "/1on1 <学生>"、"1on1 准备"。
---

# 1:1 会议调度 Skill

## 前置:拿数据布局

```
feishu_classmate_data_layout()
  → { app_token, tables: { projects, gantt, submissions, one_on_ones, tool_trace?, ... } }
```

`tables.one_on_ones` 不存在 → 提示 admin 跑 `setup-bitable`,停止。

## 场景 A:提议时间 + 创建日程

示例: `帮我约 张三 下周三下午`

1. **解析** 学生姓名 → open_id,口语时间 → 候选窗口(ISO 8601,`+08:00`)
2. **查双方忙闲**:
   ```
   feishu_calendar_freebusy({ action: "list", time_min, time_max, user_ids: ["<导师>","<学生>"] })
   ```
3. **挑 2-3 个 30min 空闲槽**,用 `feishu_ask_user_question` 给导师选(或"都不合适"重选)
4. **创建日程** (`feishu_calendar_event` action=create):
   ```
   { summary: "1on1 · <导师> × <学生>", start_time, end_time,
     user_open_id: "<导师 ou>",  // 🚨 必传,否则导师不在参会人里
     attendees: [{ type: "user", id: "<学生 ou>" }] }
   ```
5. **写 OneOnOnes** (占位,doc_token 先空):
   ```
   feishu_bitable_app_table_record({ action: "create", table_id: <one_on_ones>, fields: {
     meeting_id: "1on1_<Date.now()>_<rand>",
     supervisor_open_id: [{id:"<导师>"}], student_open_id: [{id:"<学生>"}],
     scheduled_at: <毫秒>, doc_token: "", attended: false,
     summary_md: "", action_items_json: "[]", created_at: Date.now() }})
   ```
6. 回导师: "已约 @学生 2026-04-22 14:00,会前 24h 自动整理 agenda。"

## 场景 B:会前 24h 自动准备

1. **找待准备会议**: filter `scheduled_at ∈ [now+24h, now+25h] AND doc_token=""`
2. **并行聚合**该学生近 1 周数据:
   - Gantt 进度 (`owner_open_id` + `due_date` 近一周)
   - 在投论文 (Submissions `author_open_ids`)
   - ToolTrace (若存在, 由 [evolve-telemetry](../evolve-telemetry/SKILL.md) 管理) — 近 7 天调用频次 Top-5
   - 卡住 / 逾期任务 (Assignments `status=卡住` 或超 3 天, 由 [supervisor-task-assign](../supervisor-task-assign/SKILL.md) 管理)
3. **LLM 合成 agenda markdown**:标题 + 本周进度 highlights + blockers + 论文状态 + 建议讨论话题 + 会前准备清单
4. **写 Doc**: `feishu_create_doc({ title: "1on1-<学生>-<YYYY-MM-DD>", content_md })` → 拿 `doc_token`
5. **回写 OneOnOnes**: `update` 把 `doc_token` 填上
6. **DM 双方**: "📋 明天 14:00 1on1 agenda: <doc url>"

## 场景 C:会后复盘

触发: 导师说 `1on1 纪要` 或 `/1on1 minutes <meeting_id>`

1. 调用 [meeting-minutes](../meeting-minutes/SKILL.md) skill 采集纪要
2. 回写 OneOnOnes:
   ```
   fields: { attended: true, summary_md: "<纪要 md>",
     action_items_json: "[{\"owner\":\"ou_xxx\",\"task\":\"...\",\"due\":<ms>}]" }
   ```
3. action_items 每条 → 可选自动调 [supervisor-task-assign](../supervisor-task-assign/SKILL.md) 派单

## 需要新建的多维表

### OneOnOnes

| 字段 | 类型 | 说明 |
|---|---|---|
| `meeting_id` | Text (pk) | `1on1_<ts>_<rand>` |
| `supervisor_open_id` | User | 导师 |
| `student_open_id` | User | 学生 |
| `scheduled_at` | DateTime | 约定时间(毫秒) |
| `doc_token` | Url | 议程 Doc 链接 |
| `attended` | Checkbox | 是否到会 |
| `summary_md` | Text (long) | 会后纪要 |
| `action_items_json` | Text (long) | `[{owner,task,due}]` |
| `created_at` | DateTime | 创建时间 |

## 时间与时区规则

- 所有 ISO 时间带 `+08:00`(Asia/Shanghai);默认会议时长 30 分钟
- `freebusy` 查询 `user_ids` 限 1-10 人
- 周末不自动提议(导师显式说"周六/周日"除外)

## 失败降级

- `tables.one_on_ones` 不存在 → 提示 admin 跑 `setup-bitable`,停止
- `freebusy` 查询无共同空闲 → 提示"这个时间窗双方都满,给下下周候选?"
- `feishu_calendar_event` 返回 `code 99991672` → 权限不足,引导授权 calendar scope
- `feishu_create_doc` 失败 → agenda 以纯 markdown DM,`doc_token` 留空
- `user_open_id` 未传 → 虽然能建日程但导师不在参会人 → 必须补传重试
- ToolTrace 表缺失 → agenda 省略"活跃度"分析,其余照常生成

## 示例对话

```
导师: 帮我约 张三 下周三下午
Bot:  这几个时间双方都有空:
      1. 2026-04-22 14:00-14:30
      2. 2026-04-22 15:30-16:00
      回 1/2 确认。
导师: 1
Bot:  已约 @张三 2026-04-22 14:00,会前 24h 自动整理 agenda。
```
