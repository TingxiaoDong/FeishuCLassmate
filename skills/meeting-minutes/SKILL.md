---
name: meeting-minutes
description: |
  会议纪要自动化:接收组会录音转写 / 文本笔记,结构化成"决议 / 行动项 /
  待解决问题"三栏,行动项批量写回 Gantt 表,纪要全文写入飞书 Doc 并广播群。
  所有数据操作走 `feishu_bitable_app_table_record` / `feishu_create_doc` / IM
  消息工具,本 skill 只做编排。

  **触发词**: "帮我记组会纪要"、"会议纪要"、"minutes"、"开完会了"、
  "这是今天组会的录音/笔记"、"整理一下刚才的讨论"、"action item"。
---

# 会议纪要 Skill

## 前置:拿数据布局

```
feishu_classmate_data_layout()
  → { app_token, tables: { projects, gantt, ... } }
```

行动项要写到 Gantt 表 (由 [manage-gantt](../manage-gantt/SKILL.md) 管理),
必须拿到 `tables.gantt.table_id` 和 `tables.projects.table_id`。

## 场景 A:粘贴会议笔记 / 录音转写

1. **抽取原始素材**(LLM 归一化纯文本): 文本笔记 / 语音转写 / OCR 聊天截图
2. **结构化成三栏**(LLM 本地做):
   ```
   { meeting_date: "2026-04-17",
     decisions: [{ text, rationale }],
     action_items: [{ owner_open_id, description, due_date_iso, related_project_id }],
     open_questions: [...] }
   ```
3. **消歧人员**: 对 `owner_name` 没 open_id 的行动项,list Projects 取 owner 常见匹配,
   否则 `feishu_ask_user_question` 问用户
4. **向用户确认**: `feishu_ask_user_question` pretty-print 结构化结果,**禁止未确认直接写库**
5. **批量写 Gantt 行动项**:
   ```
   feishu_bitable_app_table_record({ action:"batch_create", table_id: <gantt>, records: [
     { fields: {
       gantt_id: "g_<ts>_<rand>",
       project_id: "<related_project_id, 可空>",
       owner_open_id: [{id: "ou_xxx"}],
       milestone: "<description 前 40 字>",
       due_date: <毫秒>, progress: 0, status: "未开始",
       notes: "来自 <meeting_date> 组会纪要" }}, ...]})
   ```
6. **生成纪要 markdown** (# 组会纪要 · YYYY-MM-DD / ## 决议 / ## 行动项 表格 / ## 待解决问题)
7. **创建纪要 Doc**:
   ```
   feishu_create_doc({ title: "组会纪要-2026-04-17", content_markdown: <md> })
   → { document_id, url }
   ```
   标题前缀 `组会纪要-YYYY-MM-DD` 固定,下游统计脚本依赖此格式
8. **广播群推送**:
   ```
   {receive_id_type:"chat_id", receive_id:"<labInfo.broadcastChatId>",
    msg_type:"text", content:{text:"📝 今天组会纪要:<url>\n行动项 N 条已入 Gantt"}}
   ```
9. **DM 每个 owner**: "刚才组会给你派了 <K> 个行动项,已同步到 Gantt,详情:<doc_url>"

## 场景 B:只要纪要 Doc,不入 Gantt

触发词含 "只记一下" / "不用建任务" / "先别派活"。跳过步骤 5 和 9。

## 枚举值强约束

| 字段 | 有效值 |
|---|---|
| `Gantt.status` | `未开始`、`进行中`、`完成`、`逾期` |

时间字段一律**毫秒时间戳**。人员字段一律 `[{id:"ou_xxx"}]` 数组对象。
中文枚举值写错会触发 `1254064 / 1254066` 等 FieldConvFail 错误。

## 失败降级

- `data_layout` 返回 `app_token` 为空 → "数据库未初始化,请跑 `openclaw classmate setup-bitable`",中止
- `feishu_create_doc` 返回 `code 99991672` → 降级为把纪要贴成群消息(截断 1500 字)
- `code 1254xxx` (字段类型错) → 核对 User 字段 `[{id:...}]`、`due_date` 毫秒、`status` 中文枚举,重试一次
- 写 Gantt 时 `code 99991672` → 只产出 Doc,告知"行动项未入 Gantt,请手动建"
- 用户未在步骤 4 确认 / 回复"取消" → 中止,Doc 和 Gantt 都不写
- `labInfo.broadcastChatId` 未配 → 跳过群广播,只 Doc + DM owner
- DM 单个 owner 失败 → 日志警告,不阻塞其他 owner
- 行动项 owner 连 `feishu_ask_user_question` 都问不出 → `owner_open_id` 留空,`notes` 记"owner: <名字>"

## 示例对话

```
用户: [粘贴组会笔记...] 帮我记纪要
Bot:  结构化结果(确认后落库):
      决议: 2 条 · 行动项: 4 条(@张三 ×2, @李四 ×2) · 待决: 1 条
      确认 / 改
用户: 确认
Bot:  ✅ 纪要已建 <doc_url>,4 条行动项入 Gantt,已 DM 每位 owner。
```
