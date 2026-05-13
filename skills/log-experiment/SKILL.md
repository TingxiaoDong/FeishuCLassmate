---
name: log-experiment
description: |
  学生需要记录一次实验（假设、实验步骤、参数、指标、结果、状态）时使用。
  结构化元数据写入 Bitable `Experiments` 表，详细记录写到飞书 Doc，
  Doc URL 回写到 `Experiments` 行，形成“轻数据 + 重文本”的双轨存储。
  所有数据操作走 @larksuite/openclaw-lark 的原生 `feishu_bitable_app_table_record`
  和 `feishu_create_doc` / `feishu_update_doc`。本 skill 只做编排。

  **触发词**: "记一下实验"、"记录实验"、"experiment log"、"exp log"、
  "今天跑了个 X"、"跑完了一次 ablation"、"log 一下这次训练"、
  "/exp add …"、"补一条实验记录"。
---

# 实验记录 Skill

## 前置：总是先拿数据布局

```
feishu_classmate_data_layout()
  → { app_token, tables: { projects, experiments, ... } }
```

后续所有 bitable 操作用 `app_token` + `tables.experiments.table_id` 丢给 lark 原生工具。

---

## 字段枚举（严格）

| 字段 | 有效值 |
|---|---|
| status | `进行中`、`成功`、`失败`、`中断` |

**Agent 必须严格用以上中文值**。写错会返回 `FieldConvFail`（code 125406X）。

`Experiments` 表其它字段：`exp_id` (Text primary)、`project_id` (Text, FK by string 到 Projects, 由 [manage-gantt](../manage-gantt/SKILL.md) 管理)、
`student_open_id` (User)、`title` (Text)、`hypothesis` (Text)、`setup_md` (Text long,
作为 Doc 生成前的兜底快照)、`metrics_json` (Text, 扁平 JSON 字符串)、`result_summary` (Text)、
`doc_url` (Url, 指向详细记录 Doc)、`created_at` (DateTime ms)、`completed_at` (DateTime ms, 可空)。

---

## 场景 A：新开一条实验记录

示例: `记一下实验：今天跑了 RLHF 的 ablation，lr=1e-5, rm_scale=0.3，hypothesis 是小 rm_scale 更稳`

### 步骤

1. **解析草稿**（LLM 自己做，不调 tool）：`{ title, hypothesis, setup_md, metrics_json_draft, project_hint }`
2. **挑 project_id**：消息带 `proj_xxx` → 直接用；否则列学生在进行项目
   ```
   feishu_bitable_app_table_record({ action: "list", table_id: <projects>,
     filter: "AND(CurrentValue.[owner_open_id]=[{\"id\":\"ou_xxx\"}], CurrentValue.[status]=\"进行中\")",
     field_names: ["project_id","title"] })
   ```
   用 `feishu_ask_user_question` 让学生选一个 project
3. **确认核心字段**：用 `feishu_ask_user_question` 一次性确认 title、hypothesis、关键 metrics k/v
4. **写 `Experiments` 行**：
   ```
   feishu_bitable_app_table_record({ action: "create", table_id: <experiments>, fields: {
     exp_id: "exp_<ts>_<rand>", project_id: "proj_xxx",
     student_open_id: [{ id: "ou_xxx" }],
     title, hypothesis, setup_md,
     metrics_json: "{\"loss\":0.42,\"acc\":0.81}",
     result_summary: "", status: "进行中",
     created_at: Date.now(), completed_at: null
   }})
   ```
5. **建一份详细 Doc**：`feishu_create_doc({ title: "[EXP] <exp_id> <title>", content_md: <setup_md 全文 + hypothesis + 预期 metrics> })` → 拿到 `doc_url`
6. **回填 `doc_url`**：`action: "update"`, `fields: { doc_url: { link: "<doc_url>", text: "详细记录" } }`
7. 回学生：`✅ 已开实验 exp_xxx，状态=进行中，详细记录见 <doc_url>`

---

## 场景 B：实验跑完，回传结果

示例: `exp_xxx 跑完了，acc=0.83，比 baseline 好 2pt，成功` / `那个 ablation 中断了`

### 步骤

1. 查 record_id：`filter: "CurrentValue.[exp_id]=\"exp_xxx\""`
2. **更新 Experiments 行**：
   ```
   fields: {
     status: "成功",                    // 严格枚举
     result_summary: "acc=0.83, +2pt vs baseline",
     metrics_json: "{\"acc\":0.83,\"baseline\":0.81}",
     completed_at: Date.now()
   }
   ```
3. **追写到 Doc**：用 `feishu_update_doc` 在原 Doc 末尾追加 `## 结果` 段落，含最终 metrics 表和结论
4. 回学生 `✅ 已归档`

---

## 场景 C：24h 自动追问（由 cron 触发，本 skill 只回响应）

系统每 24h 扫 `status=进行中 AND created_at < now-24h` 的行，给 `student_open_id` 发 DM：

```
⏰ 实验 {title} (exp_xxx) 开着已 24h+，跑完了吗？
回复：[成功|失败|中断|还在跑]
```

学生回复后，进入**场景 B** 流程；若回 `还在跑` → 不更新表，下次 cron 再追问。

---

## 场景 D：查询学生/项目的实验记录

示例: `我最近跑了哪些实验？` / `proj_rlhf 下有哪些 exp？`

```
feishu_bitable_app_table_record({
  action: "list",
  filter: "AND(CurrentValue.[student_open_id]=[{\"id\":\"ou_xxx\"}], CurrentValue.[created_at].isGreater(<now-7d>))",
  field_names: ["exp_id","title","status","result_summary","doc_url"],
  sort: [{ field_name: "created_at", desc: true }]
})
```

格式化：每行 `🧪 exp_xxx [status] title — summary (doc)`，最多 10 条。

---

## 失败降级

- `feishu_create_doc` 失败 → 不阻塞，仍创建 `Experiments` 行，把 `setup_md` 全量存在表里；
  告知学生 "Doc 创建失败，详细记录已存在表里的 setup_md 字段"，返回 record_id
- lark `code 99991672` (缺 scope) → "bitable/doc 权限不足，请 admin 联系"，停止
- lark `code 125406X` (FieldConvFail) → 重点检查 `status` 枚举、`created_at/completed_at` 必须毫秒时间戳
- lark `code 1254068` (Url 转换失败) → `doc_url` 必须是 `{link, text}` 对象
- 学生没给 project_id 且 Projects 表为空 → 允许 `project_id: ""`，提示学生“建议先建项目”
- `feishu_classmate_data_layout` 返回 `app_token` 为空 → "数据库未初始化，请运行 `openclaw classmate setup-bitable`"
