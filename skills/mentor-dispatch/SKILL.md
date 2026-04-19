---
name: mentor-dispatch
description: |
  新人在群里抛出技术问题时,自动匹配并 DM 合适的师兄师姐;
  回答归档到 `MentorAnswers` 表,沉淀为实验室 FAQ 语料。
  所有 bitable 操作走 @larksuite/openclaw-lark 的
  `feishu_bitable_app_table_record`,本 skill 只负责匹配打分与话术。

  **触发词**: "问个问题:..."、"@bot 求教"、"请教一下"、
  "有人会 xxx 吗"、"救救孩子"、师兄回答后的归档指令。
---

# Mentor Dispatch Skill

## 前置:总是先拿数据布局

```
feishu_classmate_data_layout()
  → { app_token, tables: { ..., skill_tree, projects, tool_trace, mentor_answers } }
```

---

## 需要新建的多维表

### MentorAnswers

| 字段 | 类型 | 说明 |
|---|---|---|
| answer_id | Text (pk) | `ma_<ts>_<rand>` |
| question_text | Text | 原始问题全文 |
| asker_open_id | User | 提问者 |
| answerer_open_id | User | 回答的师兄师姐 |
| question_chat_id | Text | 问题所在群的 chat_id(跳回原帖用) |
| answer_md | Text | 师兄回答(markdown) |
| tags | MultiSelect | 技术标签,和 SkillTree.skill_tag 同 preset (由 [skill-tree](../skill-tree/SKILL.md) 管理) |
| created_at | DateTime | 毫秒 |
| helpful | Checkbox | 提问者事后确认是否有用 |

> 该表同时作为 `lab-faq-search` skill(可能由其他 agent 后续新增)的查询语料源。

---

## 场景 A:新问题进来 → 匹配候选师兄师姐

**触发来源**:群内消息以 `问个问题:` / `请教一下` / `@bot 求教` 开头;或 `@bot` 被点名且正文含问号。

### 步骤

1. **抽关键词**(LLM 自己做,不调工具):
   ```
   { keywords: ["ROS2","tf2_ros","静态 transform"], urgency: "普通" }
   ```
2. **查技能树**:
   ```
   feishu_bitable_app_table_record({
     action: "list",
     app_token, table_id: <skill_tree>,
     filter: "OR(CurrentValue.[skill_tag].contains(\"ROS2\"), CurrentValue.[skill_tag].contains(\"tf2_ros\"))",
     field_names: ["student_open_id","skill_tag","proficiency","last_used_at"]
   })
   ```
3. **查项目关键词**(并行):
   ```
   feishu_bitable_app_table_record({
     action: "list", app_token, table_id: <projects>,
     filter: "OR(CurrentValue.[keywords].contains(\"ROS2\"), ...)",
     field_names: ["project_id","owner_open_id","keywords"]
   })
   ```
4. **(可选)查活跃度**:最近 7 天的 `ToolTrace`,按 `caller_open_id` 聚合调用次数
5. **打分与排序**(LLM 聚合):
   - `skill_match`: 命中标签数 × `proficiency` 权重(入门 1 / 熟练 2 / 精通 3 / 可教 4)
   - `project_match`: 命中项目关键词 +2
   - `activity`: 最近 7 天调用次数 log1p
   - **过滤**:不是提问者本人;不在 `labInfo.onLeave` 请假名单
   - 排序取 top-2
6. **DM 两位候选**(话术):
   > 有个师弟/师妹在 <chat 链接> 问 `<问题摘要>`,
   > 你最近在做 <相关项目标题>,方便搭把手吗?
   > 回复 `接` / `没空` 即可。

---

## 场景 B:师兄回答 → 归档

师兄直接在原群回复提问者,或先私聊 agent 回复。agent 通过以下任一方式捕捉:
- 提问者说 `@bot 这条回答挺有用,存一下`
- 师兄自己说 `@bot 归档 上条回答`
- 超时未响应 → 场景 C

### 步骤

1. 用 `feishu_ask_user_question` 向回答者确认回答全文(如是多条消息,拼成 markdown)
2. 提取 tags(LLM 复用 `SkillTree` preset 标签列表)
3. 写 `MentorAnswers`:
   ```
   feishu_bitable_app_table_record({
     action: "create",
     app_token, table_id: <mentor_answers>,
     fields: {
       answer_id: "ma_<ts>_<rand>",
       question_text: "<原问题>",
       asker_open_id: [{ id: "<提问者>" }],
       answerer_open_id: [{ id: "<回答者>" }],
       question_chat_id: "<oc_xxx>",
       answer_md: "<回答 markdown>",
       tags: ["ROS2","tf2_ros"],
       created_at: Date.now(),
       helpful: false
     }
   })
   ```
4. 24h 后私聊提问者:"上次 <问题> 的回答,有用吗?回复 `有用` 我打勾。"
   - 若 `有用` → `action: "update"`,`fields: { helpful: true }`

---

## 场景 C:超时升级

**触发**:场景 A 发出后 24h 内,两位候选都未私聊 agent `接`,也没在群里 @ 提问者。

### 步骤

1. 查提问者的 supervisor(从 `labInfo.supervisors` 映射)
2. DM 导师:
   > <学生姓名> 24h 前问 `<问题摘要>`,目前无人响应,
   > 请 @ 合适的师兄师姐,或直接回复解答。
3. 导师 ack 后,结束升级流程

---

## 场景 D:FAQ 命中前置

在进入场景 A 之前,可先扫一遍 `MentorAnswers` 做相似问题命中:

```
feishu_bitable_app_table_record({
  action: "list",
  app_token, table_id: <mentor_answers>,
  filter: "OR(CurrentValue.[tags].contains(\"ROS2\"), ...)",
  field_names: ["question_text","answer_md","helpful"]
})
```

若找到 `helpful=true` 的相似条目 → 先把历史回答甩给提问者,
附一句 "如果解决了就不打扰师兄了,回复 `还没解决` 我会继续派单。"

> 正式的语义检索由 [lab-faq-search](../lab-faq-search/SKILL.md) skill 处理,本 skill 只做 tag 粗筛。

---

## 失败降级

- `SkillTree` 表不存在 → 跳过场景 A 步骤 2,仅依赖 `Projects` 关键词匹配
- `Projects` 也查空 → 降级为把问题直接群 @ `labInfo.supervisors`
- 未能抽到任何关键词(LLM 识别失败)→ 回复提问者 "问题太抽象,能补个最小复现例子吗?"
- lark 返回 `code 99991672` → 告知触发者权限不足并停止
- 写 `MentorAnswers` 字段校验错(code 1254xxx)→ 用 preset 标签过滤掉未登记的 tag,重试一次
