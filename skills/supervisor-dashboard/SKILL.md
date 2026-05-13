---
name: supervisor-dashboard
description: |
  导师一键式实验室总览面板。聚合学生进度、逾期节点、论文投递、设备借用、
  周报发布与学生活跃度,输出一份简洁的中文 Markdown 面板到 DM。
  所有数据查询走 @larksuite/openclaw-lark 的原生 `feishu_bitable_app_table_record`,
  本 skill 只做编排 + LLM 综合成文。

  **触发词**: "dashboard"、"实验室情况"、"所有学生进度"、"整体怎么样"、
  "/dashboard"、"/dashboard student=<name_or_open_id>"。
---

# 导师总览面板 Skill

## 前置:拿数据布局

```
feishu_classmate_data_layout()
  → { app_token, tables: { projects, gantt, equipment, submissions, weekly_digests, research, ... } }
```

⚠️ 并行 agent 可能会追加新表(例如 ToolTrace、Assignments、OneOnOnes)。
**必须运行时用 `data_layout()` 返回的 `tables` map 做 key 存在性检查**,
找不到的表直接跳过对应的 section,不要 hardcode。

---

## 场景 A:全实验室总览(`/dashboard`)

### 步骤

1. 调 `feishu_classmate_data_layout()` 拿到 app_token 和 tables
2. **并行**(单条消息内同时发多个 tool call)查以下数据:

   **a. 本周新开/完成的 milestones** — 按学生分组
   ```
   feishu_bitable_app_table_record({
     action: "list",
     app_token, table_id: <gantt>,
     filter: "AND(CurrentValue.[due_date]>=<本周一毫秒>, CurrentValue.[due_date]<=<本周日毫秒>)",
     field_names: ["gantt_id","milestone","owner_open_id","status","progress","due_date","notes"]
   })
   ```

   **b. 所有逾期 milestones**
   ```
   filter: "AND(CurrentValue.[status]!=\"完成\", CurrentValue.[due_date]<<Date.now()>)"
   ```

   **c. 在投/未决论文** (from Submissions)
   ```
   filter: "OR(CurrentValue.[status]=\"已投\", CurrentValue.[status]=\"审稿中\", CurrentValue.[status]=\"major revision\", CurrentValue.[status]=\"minor revision\")"
   ```

   **d. 在借设备**
   ```
   filter: "CurrentValue.[state]=\"借出\""
   sort:   [{field_name:"expected_return", desc:false}]
   ```

   **e. 本周发布的 Research 周报**
   ```
   table_id: <research>,
   filter: "CurrentValue.[week]=\"<ISO 周,如 2026-W16>\""
   ```

3. **学生活跃度快照**:
   - 从 `chat_should_engage` tool(如果该 session 有 last_interaction 记录)或 `ToolTrace`(若已建表)
     拉每个学生 `last_interaction` 时间戳
   - 过滤出 `Date.now() - last_interaction > 3*86400_000` 的学生,列入"最近 3 天无活动"

4. **LLM 综合成文** — 生成以下结构的中文 Markdown:

```markdown
# 📊 实验室总览 · {YYYY-MM-DD}

## 🎯 本周进度(按学生)
- **张三** · 完成 2 / 在进行 1 / 未开始 0
  - ✅ 2026-04-15 《PPO baseline》 100%
  - 🚧 2026-04-19 《消融实验》 60% · "正在跑 seed 3/5"
- **李四** · ...

## 🔴 逾期节点(共 N 条)
| 学生 | 节点 | 计划日期 | 延期天数 |
|---|---|---|---|
| 张三 | XXX | 2026-04-10 | 7 天 |

## 📝 在投/未决论文(共 N 篇)
- 《XXX》· NeurIPS 2026 · 审稿中 · 决定 2026-08-01
- 《YYY》· ICML 2026 · major revision · 截止 2026-05-20

## 🔧 在借设备(共 N 件)
| 器材 | 借用人 | 应归还 | 备注 |
|---|---|---|---|
| 示波器 | 李四 | 2026-04-20 | 做信号分析 |

## 📚 本周 Research 周报
- 2026-W16 · 《Diffusion Policy 综述》· 王五

## ⚠️ 最近 3 天未活跃
- 赵六(last: 2026-04-12)
- ...
```

5. **发送到 DM**:
   - 单条消息 > 5000 字符 → 自动按 section 分 2-3 条发送
   - 用 `feishu_im_bot_text` 或 skill 默认 DM 通道

---

## 场景 B:单个学生视图(`/dashboard student=<name_or_open_id>`)

相同流程,但所有 `feishu_bitable_app_table_record` 查询加一个 filter:
```
CurrentValue.[owner_open_id]=[{"id":"<target open_id>"}]
```

- 若用户传的是姓名(非 open_id)→ 先用 `feishu_contact_user` 查 open_id,不到则 ask_user_question 确认
- 学生视图多加一块"**近期 5 次提交/对话摘录**"(从 ToolTrace,如果表存在)

---

## 输出规范

- **时间**: 一律 `YYYY-MM-DD`(不显示秒)
- **百分比**: 整数,不带小数
- **逾期标记**: 红色 emoji `🔴` 或 `⚠️`
- **学生名字**: 用 `@open_id` 格式,飞书会自动渲染成 @提及
- 每个 section 若为空 → 显式写"(无)",不要省略标题

---

## 失败降级

- `data_layout` 返回 `app_token` 为空 → 回复"数据库未初始化,请联系管理员跑 `openclaw classmate setup-bitable`",停止
- 某张表 `table_id` 不存在(并行 agent 尚未建) → 跳过对应 section,在面板末尾加一行 `> ⚠️ 部分数据未接入: [表名]`
- lark 返回 `code 99991672` (缺 scope) → 回复"权限不足,请管理员加 scope",停止
- 单个 `list` 调用超时或返回错误 → 对应 section 写 "(查询失败,已跳过)",其余 section 继续输出
- 总字符 > 5000 → 按 H2 分块,每块 ≤ 4500 字符,序号 `(1/N)` 前缀

---

## 与其他 skill 的配合

- 面板底部可追加一行 CTA:"`/weekly-digest` 生成完整周报 | `/1on1` 约个 1:1 聊聊"
- 本 skill **只读**,不写任何表
