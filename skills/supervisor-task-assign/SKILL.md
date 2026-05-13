---
name: supervisor-task-assign
description: |
  导师自然语言派任务给学生,解析 → 确认 → 落表 → DM 学生 → 驱动状态流转。
  所有表操作走 @larksuite/openclaw-lark 的原生 `feishu_bitable_app_table_record`。
  同时支持学生侧"我有哪些任务?"查询。

  **导师触发词**: "给 <同学> 派任务"、"assign xxx to do yyy"、"让 @xxx 去做 zzz"、
  "安排 <学生> 做 <事情>"。
  **学生触发词**: "我有哪些任务"、"我的待办"、"接受"、"有问题"、"卡住了"。
---

# 导师派任务 Skill

## 前置:拿数据布局

```
feishu_classmate_data_layout()
  → { app_token, tables: { projects, gantt, assignments, ... } }
```

如果 `tables.assignments` 不存在,先提示管理员跑 `setup-bitable` 建 `Assignments` 表(见下)再继续。

---

## 需要新建的多维表

### Assignments(声明式 — 由 setup.ts 的并行 agent 建)

| 字段 | 类型 | 说明 | 枚举(严格中文) |
|---|---|---|---|
| `assign_id` | Text 主键 | `assign_<ts>_<rand>` | — |
| `assigner_open_id` | User | 派单导师 | — |
| `assignee_open_id` | User | 被指派学生 | — |
| `title` | Text | 任务标题 ≤ 40 字 | — |
| `description` | Text long | 描述 / 验收标准 | — |
| `parent_project_id` | Text | 关联项目(可选,FK Projects) | — |
| `priority` | SingleSelect | 优先级 | **`低`**、**`中`**、**`高`**、**`紧急`** |
| `due_date` | DateTime | 截止(毫秒) | — |
| `status` | SingleSelect | 状态 | **`待接收`**、**`进行中`**、**`已完成`**、**`已取消`**、**`卡住`** |
| `assigned_at` | DateTime | 创建时间 | — |
| `completed_at` | DateTime | 完成时间 | — |

---

## 场景 A:导师派任务

示例: `给李同学派个任务:把 PPO baseline 跑通,下周五前完成,优先级高`

1. **LLM 解析**: `{ assignee_hint, title, description, due_date_iso, priority, parent_project_hint }`
2. **补 assignee_open_id**: 姓名 → `feishu_contact_user` 查 ou_xxx;歧义用 `feishu_ask_user_question` 让导师选
3. **确认卡** (`feishu_ask_user_question`):
   ```
   指派给: 李四 (ou_xxx) · 标题: ... · 截止: 2026-04-24 23:59
   优先级: 高 · 关联项目: (无)
   回复 "确认" 落单,"改 <字段>" 编辑。
   ```
4. **写 Assignments**:
   ```
   feishu_bitable_app_table_record({
     action: "create", app_token, table_id: <assignments>,
     fields: {
       assign_id: "assign_<Date.now()>_<rand>",
       assigner_open_id: [{ id: "<导师 ou>" }],
       assignee_open_id: [{ id: "<学生 ou>" }],
       title, description, parent_project_id: "",
       priority: "高", status: "待接收",
       due_date: <毫秒>, assigned_at: Date.now(), completed_at: null
     }
   })
   ```
5. **(可选)挂 Gantt** (由 [manage-gantt](../manage-gantt/SKILL.md) 管理): 若确认关联 `project_id`,再 create 一条 Gantt,`milestone=title`,`status="未开始"`,`notes="from assignment <assign_id>"`
6. **DM 学生**:
   ```
   📌 导师 @<导师> 给你派了任务
   **<title>** · 优先级 <priority> · 截止 <due YYYY-MM-DD>
   <description>
   回复 `接受` / `有问题` / `完成` / `卡住了 <原因>` 驱动流转。
   ```
7. 回复导师: "已派单,assign_id=<xxx>"

---

## 场景 B:学生侧状态流转

先 `action=list` + filter `assign_id=<xxx>` 拿 record_id,再 update:

| 学生回复 | 更新字段 | 额外动作 |
|---|---|---|
| `接受` | `status=进行中` | — |
| `有问题` + 具体内容 | 不改 status | DM 导师"学生对 X 有疑问: ..." |
| `完成` / `done` | `status=已完成`, `completed_at=Date.now()` | DM 导师 |
| `卡住了 <原因>` | `status=卡住`, `description` 末尾追加原因 | DM 导师 |
| `取消` | `status=已取消` | — |

---

## 场景 C:学生查自己的任务

触发: `我有哪些任务?` / `我的待办`

```
feishu_bitable_app_table_record({
  action: "list", table_id: <assignments>,
  filter: "AND(CurrentValue.[assignee_open_id]=[{\"id\":\"<学生 ou>\"}], NOT(OR(CurrentValue.[status]=\"已完成\", CurrentValue.[status]=\"已取消\")))",
  sort: [{ field_name: "due_date", desc: false }]
})
```

按优先级分组输出,紧急置顶:
```
## 我的任务 (共 N)
### 🔥 紧急
- 《PPO baseline》 · 截止 2026-04-24 · 进行中
### 🟠 高
...
```

---

## 场景 D:导师查自己派过的任务

触发: `我派过的任务` / `<学生> 的任务`。filter 改 `assigner_open_id=[{id:"<导师>"}]`,其余同 C。

---

## 枚举值强约束

写错会报 lark `code 1254062` FieldConvFail,自查后重试一次,第二次失败直接报错给用户。
- **priority**: `低`、`中`、`高`、`紧急`
- **status**: `待接收`、`进行中`、`已完成`、`已取消`、`卡住`

---

## 失败降级

- `tables.assignments` 不存在 → "任务表未建,请管理员跑 `openclaw classmate setup-bitable`",停止
- 找不到 assignee open_id(歧义 + ask 超时) → 不落单,告知"无法锁定学生,已取消"
- DM 学生失败(未加机器人) → 落单成功,提示导师"已记录,但学生未启用机器人,请手动通知"
- `due_date` 早于当前时间 → ask 二次确认"截止日期已过,是否仍创建?"
- lark `code 99991672` (缺 scope) → "权限不足,请管理员加 scope",停止
