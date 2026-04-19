---
name: meeting-agenda
description: |
  组会议程筹备:会前 24h 收集议题、生成议程 Doc、广播到实验室群、
  会前提醒参会人准备。所有产出走 @larksuite/openclaw-lark 的原生
  `feishu_create_doc` / `feishu_update_doc` / IM 消息 / `feishu_ask_user_question`,
  本 skill 只负责流程编排。

  **触发词**: "组会议程"、"准备组会"、"明天组会"、"we have a group meeting tomorrow"、
  "下周二 group meeting"、"开会前议程"。
---

# 组会议程 Skill

## 前置:拿数据布局

```
feishu_classmate_data_layout()
  → { app_token, tables: { projects, gantt, ... } }
```

议程本身不落表,但要能从 `Projects` 表反查参会人的在研项目,丰富议题。

---

## 场景 A:用户说"帮我准备下周二的组会"

### 步骤

1. **确定会议时间**。先尝试:
   ```
   feishu_calendar.list_events({ time_min: <now>, time_max: <now+7d> })
   ```
   如果 lark-mcp 没暴露 calendar 工具,或返回空,直接用 `feishu_ask_user_question`
   问用户具体 `YYYY-MM-DD HH:mm`。不要乱猜。

2. **确定参会人**。`feishu_ask_user_question`:
   > 参会的是谁?给我 open_id 列表,或者逐个 @ 他们也行。
   >
   > (默认:所有 Projects 表里 `status=进行中` 的 `owner_open_id` 去重)

   拿不到 open_id 时退化:问名字,把名字列进议程即可(后续 DM 步骤跳过)。

3. **为每人收集议题**。对每个参会人,并发 DM:
   ```
   {receive_id_type: "open_id", receive_id: "ou_xxx",
    msg_type: "text",
    content: {text: "下周二 <HH:mm> 组会,你想讨论哪几个话题?有要大家预习的材料吗?
                     一条消息回我即可,我帮你放进议程。"}}
   ```
   最多等 2 小时,到点没回复的人 topic 留 `"(未提交)"`。

4. **丰富议题上下文**。对每个人的 `open_id`,拉 Projects 给 LLM 做背景:
   ```
   feishu_bitable_app_table_record({
     action: "list",
     app_token, table_id: <projects>,
     filter: {
       conjunction: "and",
       conditions: [
         { field_name: "owner_open_id", operator: "contains", value: ["ou_xxx"] },
         { field_name: "status", operator: "is", value: ["进行中"] }
       ]
     },
     field_names: ["title","abstract_doc_token","updated_at"]
   })
   ```
   用来在议程里自动附"相关项目:<title>"。

5. **生成议程 markdown**:
   ```
   # 组会议程 · 2026-04-21 10:00-11:30

   ## 时间地点
   2026-04-21 10:00–11:30  @ 实验室会议室

   ## 参会人
   - @张三  @李四  @王五  @赵六

   ## 议题(按人)
   ### 张三 · 30min
   - 话题 1:...
   - 话题 2:...
   - 相关项目:<title>
   - 预习材料:<url>

   ### 李四 · 20min
   ...

   ## 目标产出
   - 确认下周实验计划
   - 敲定 XX 论文投稿截止

   ## 预习资料清单
   1. [xxx](link)
   2. ...
   ```
   时长按人数平均分,LLM 自己算。

6. **创建议程 Doc**:
   ```
   feishu_create_doc({
     title: "组会议程-2026-04-21",
     content_markdown: <上面那段 markdown>,
     folder_token: <可选,如果 config 有 docs.publicProjects 的父目录就用那个>
   })
   → 返回 { document_id, url }
   ```

7. **广播群推送 Doc 链接**:
   ```
   {receive_id_type: "chat_id",
    receive_id: "<labInfo.broadcastChatId>",
    msg_type: "text",
    content: {text: "📋 下周二组会议程来了:<url>\n请各位会前把自己那栏确认下。"}}
   ```

8. **会前 24h 提醒**(调度):
   - 如果本次调用离会议时间 >24h:挂一个延时(setTimeout 或 cron)到 T-24h 再触发 §场景 B
   - 如果 <24h:立即 §场景 B

---

## 场景 B:会前 24h DM 提醒

对每个参会人:
```
{receive_id_type: "open_id", receive_id: "ou_xxx",
 msg_type: "text",
 content: {text: "明天 <HH:mm> 组会,记得准备:\n- 你的议题:…\n- 预习材料:<url>\n
                  议程全文:<doc_url>"}}
```
DM 失败的人(离职/退群)日志警告,不阻塞。

---

## 字段/参数约束

- `receive_id_type` 必须是 `"open_id"`(发 DM)或 `"chat_id"`(发群)之一。
- `feishu_create_doc` 返回的 `url` 才是能发群的那个,不是 `document_id`。
- 议程 Doc 标题格式固定 `组会议程-YYYY-MM-DD`,下游脚本依赖这个前缀。
- 广播文本不要超过 1500 字,超了就只发摘要 + Doc 链接。

---

## 失败降级

- calendar 工具不可用 → 直接 `feishu_ask_user_question` 问用户,不要猜。
- `feishu_create_doc` 返回 `code 99991672` (缺 scope `docx:document`) →
  降级为把议程贴成群消息(纯文本,截断到 1500 字内),告诉用户"无 Doc 权限,
  已直接发群"。
- `labInfo.broadcastChatId` 未配 → 跳过广播步骤,只创建 Doc 并把 URL 返回给用户。
- 所有参会人 2h 内都没回议题 → 生成"空白模板"议程(只有时间地点参会人),
  通知召集人手动补齐。
- DM 单个参会人失败 → 日志警告,跳过,继续整体流程。
- 会议时间已过 → 中止并提示用户"这个时间已过,要不要改成下次组会"。
