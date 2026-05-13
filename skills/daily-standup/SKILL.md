---
name: daily-standup
description: |
  每日早会自动化:工作日 09:30 向实验室广播群发布 standup 摘要,聚合每位成员
  昨日进度(自动从 Gantt 拉)、今日计划(DM 问学生一行)、卡点。
  所有数据操作走 @larksuite/openclaw-lark 的原生 `feishu_bitable_app_table_record` /
  `feishu_create_doc` / `feishu_update_doc` / IM 消息工具,本 skill 只做编排。

  **触发词**: "早会"、"standup"、"每日站会"、"daily standup"、"09:30"、
  cron 触发 `daily-standup`、"今天完成了 …"(学生对早会 DM 的回复)。
---

# 每日早会自动化 Skill

## 前置:拿数据布局

```
feishu_classmate_data_layout()
  → { app_token, tables: { projects, gantt, equipment, research, standups? } }
```

所有 bitable 操作直接用返回的 `app_token` + `tables[x].table_id` 丢给 lark 原生工具。

`tables.standups` 缺失 → 提示 admin 跑 `setup-bitable`,停止。

---

## 场景 A:cron 09:30 触发的批量早会

### 步骤

1. **枚举成员**。优先方式:
   ```
   feishu_bitable_app_table_record({
     action: "list",
     app_token, table_id: <projects>,
     field_names: ["owner_open_id"]
   })
   ```
   对结果 `owner_open_id` 去重。`contact.base:readonly` scope 通常不可用,不要强依赖。

2. **拉昨日进度**。对每个 `open_id`:
   ```
   feishu_bitable_app_table_record({
     action: "list",
     app_token, table_id: <gantt>,
     filter: {
       conjunction: "and",
       conditions: [
         { field_name: "owner_open_id", operator: "contains", value: ["ou_xxx"] },
         { field_name: "notes", operator: "isNotEmpty", value: [] }
       ]
     }
   })
   ```
   LLM 按 `updated_at > Date.now()-86400_000` 再做一次内存过滤(Gantt 表 `updated_at`
   字段不存在时退化为全部近期 notes),把 `notes + milestone + progress` 拼成
   "昨日完成" 一句话。

3. **DM 每个成员**(用 lark 原生 IM 文本消息工具,发到 chat_type=p2p):
   ```
   {receive_id_type: "open_id", receive_id: "ou_xxx",
    msg_type: "text",
    content: {text: "早安。昨日我帮你看了一下:\n<yesterday>\n\n今天打算做什么?一行回我。有卡点也说。"}}
   ```

4. **等待回复**。两种策略,选一:
   - 轻量:`await new Promise(r => setTimeout(r, 2*60*60*1000))` 两小时后强制汇总
   - 交互:用 `feishu_ask_user_question` 同步等待每个成员

5. **解析回复**。LLM 把学生一段话拆成 `today` + `blockers`(若没提卡点则 `blockers=""`)。

6. **批量写 Standups**:
   ```
   feishu_bitable_app_table_record({
     action: "batch_create",
     app_token, table_id: <standups>,
     records: [
       { fields: {
         standup_id: "su_<ts>_<rand>",
         date: "2026-04-17",
         student_open_id: [{id: "ou_xxx"}],
         yesterday: "...",
         today: "...",
         blockers: "...",
         created_at: Date.now()
       }},
       ...
     ]
   })
   ```

7. **生成摘要 markdown**:
   ```
   ## 🌅 早会 2026-04-17
   - @张三 · 昨日 …  · 今日 …  · 🚧 卡点 …
   - @李四 · 昨日 …  · 今日 …
   ...
   今日整体卡点: N 个,其中 M 个需要导师关注。
   ```

8. **追加到日常记录 Doc**:
   ```
   feishu_update_doc({
     document_id: <docs.dailyRecord 的 doc_id>,
     // append 一个新 block,内容为上面的 markdown
   })
   ```
   写入前先 `feishu_fetch_doc` 看最末 block,避免把早会插到奇怪位置。

9. **广播群推送**:
   ```
   {receive_id_type: "chat_id",
    receive_id: "<labInfo.broadcastChatId>",
    msg_type: "text",
    content: {text: "<上面那段 markdown>"}}
   ```

---

## 场景 B:学生主动回 "我今天做 X"

学生没等 cron 直接发消息,也能触发单条 standup。步骤 3-6 单独跑,`yesterday` 留空
或从 Gantt 现拉。

---

## 需要新建的多维表

### Standups

| 字段 | 类型 | 说明 |
|---|---|---|
| `standup_id` | Text (pk) | `su_<ts>_<rand>` |
| `date` | Text | `YYYY-MM-DD` 方便筛选 |
| `student_open_id` | User | `[{id:"ou_xxx"}]` |
| `yesterday` | Text | 昨日进度摘要 |
| `today` | Text | 今日计划 |
| `blockers` | Text | 卡点,可空 |
| `created_at` | DateTime | 毫秒时间戳 |

## 字段枚举(严格)

Standups 表没有 SingleSelect,不设枚举。时间字段 `created_at` 用**毫秒时间戳**。
`student_open_id` 必须是 `[{id:"ou_xxx"}]` 数组对象,绝不能是裸字符串。

---

## 失败降级

- `feishu_classmate_data_layout` 返回 `app_token` 为空 → 告诉用户"数据库未初始化,
  请联系管理员跑 `openclaw classmate setup-bitable`",中止。
- `tables.standups` 缺失 → 按前置 §Standups 表存在性检查 引导 admin 建表,中止本次。
- `labInfo.broadcastChatId` 未配 → 只写 Doc + DM 当事人,跳过群广播,给用户提示。
- lark 返回 `code 99991672` (缺 scope) → 告诉用户"权限不足",中止。
- lark 返回 `code 1254xxx` (字段类型错) → 核对 User 字段格式 `[{id:...}]`、
  `created_at` 毫秒,重试一次。
- 两小时内某成员未回复 → `today` 字段写 `"(未回复)"`,`blockers` 留空,照常汇总。
- DM 失败(学生离职/退群) → 日志警告,跳过该成员不阻塞整体流程。
