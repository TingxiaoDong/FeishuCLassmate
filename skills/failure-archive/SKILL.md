---
name: failure-archive
description: |
  实验室"失败博物馆":归档每次失败实验的根因 / 教训 / 绕行方案,
  让后来的同学不要在同一个坑上再翻车一次。
  所有数据写入走 @larksuite/openclaw-lark 原生 `feishu_bitable_app_table_record`,
  长文档用 `feishu_create_doc` / `feishu_update_doc` 存 markdown 完整版。
  本 skill 只负责问答编排 + TL;DR 生成(LLM 本地做)。

  **触发词**: "记个教训"、"实验失败了"、"failure archive"、"post-mortem"、
  "以后别踩这个坑"、"这个坑要记一下"、"failure log"。
---

# 失败归档 Skill

## 前置:总是先拿数据布局

```
feishu_classmate_data_layout()
  → { app_token, tables: { projects, failure_archive, ... } }
```

所有对 `FailureArchive` 表的读写都用 `tables.failure_archive.table_id` + `app_token`。

---

## 需要新建的多维表

`FailureArchive`(admin 稍后在 `src/bitable/schema.ts` 加 TableDef):

| 字段 | 类型 | 备注 |
|---|---|---|
| failure_id | Text (pk) | 形如 `fail_<ts>_<rand>` |
| reporter_open_id | User | `[{id:"ou_xxx"}]` |
| title | Text | 例:"Why PPO on 4-leg 不 work" |
| category | SingleSelect | `硬件` / `仿真` / `训练` / `调参` / `部署` / `数据` / `环境配置` / `其他` |
| context_md | Text long | 当时在尝试什么 |
| failure_description_md | Text long | 具体哪里炸了 |
| root_cause_md | Text long | 根因分析 |
| workaround_or_lesson_md | Text long | 绕行方案 / 后人可以这样做 |
| tldr | Text | **自动生成的 1 句话总结**,用于搜索命中排序 |
| related_project_id | Text (FK Projects) | project_id 字符串(由 [manage-gantt](../manage-gantt/SKILL.md) 管理) |
| tags | MultiSelect | 关键词,如 `PPO`、`CUDA`、`ROS noetic` |
| related_paper_urls | Text | 逗号分隔 URL |
| hours_wasted | Number | 大致被卡的小时数 |
| doc_url | Url | `feishu_create_doc` 返回的完整文档链接(可选) |
| created_at | DateTime | 毫秒时间戳 |

**枚举值必须严格用中文**,写错会报 `FieldConvFail` (code 125406X)。

---

## 场景 A:学生登记新失败

示例:`记个教训:在 IsaacSim 里开 4 只腿的 PPO,reward 一直原地震荡,查了 3 天发现是 action scale 没归一化`

### 步骤

1. LLM 解析初稿,抽出:title / category / context / failure_description / root_cause / lesson / tags / hours_wasted。
2. 用 `feishu_ask_user_question` 逐字段让学生确认或补全(尤其 category 要落到枚举值上)。
3. LLM 本地生成 **TL;DR**(≤ 60 字),形如"action 未归一化导致 PPO reward 震荡,记得归一化到 [-1,1]"。
4. **写 FailureArchive 行**:
   ```
   feishu_bitable_app_table_record({
     action: "create",
     app_token, table_id: <failure_archive>,
     fields: {
       failure_id: "fail_<ts>_<rand>",
       reporter_open_id: [{ id: "<学生 open_id>" }],
       title, category, tldr,
       context_md, failure_description_md,
       root_cause_md, workaround_or_lesson_md,
       related_project_id, tags,
       related_paper_urls, hours_wasted,
       created_at: Date.now()
     }
   })
   ```
5. 若 `context_md` 或 `failure_description_md` 超过 ~2000 字,额外用 `feishu_create_doc` 建长文档,回填 `doc_url`(`feishu_bitable_app_table_record.update`)。
6. 回复学生:"已归档 🪦,后人感谢你。TL;DR: <tldr>"。

---

## 场景 B:搜相似失败

示例:`search failure about ppo diverge` / `之前有没有人踩过 CUDA mismatch 的坑`

### 步骤

1. LLM 抽关键词 → `["ppo","diverge"]`。
2. `feishu_bitable_app_table_record({ action: "list", filter: "OR(CurrentValue.[title].contains(\"ppo\"), CurrentValue.[tags].contains(\"ppo\"), CurrentValue.[tldr].contains(\"ppo\"))" })`
3. 对命中行按 tldr/tags 匹配度本地排序,取 top 3。
4. 格式化输出:
   ```
   🔍 找到 3 条类似失败:
   1. [fail_xxx] Why PPO on 4-leg 不 work — action 未归一化 (8h 坑)
      → 绕行:把 action clip 到 [-1,1] 再喂 env
   2. ...
   ```
5. 若 0 命中 → "还没人踩过这个坑,要不要现在登记一条?"(诱导学生走场景 A)。

---

## 场景 C:周会广播

**触发**: cron service `failure-archive-weekly` 自动触发(周五 17:00)。

1. `feishu_bitable_app_table_record({ action: "list", filter: "CurrentValue.[created_at]>=<本周一 ts>" })`
2. 统计本周新增 N 条,按 category 分桶。
3. 在 `labInfo.broadcastChatId` 群里广播:
   ```
   🪦 本周新增 N 条 failure archive:
   - 训练 × 2 / 硬件 × 1 / 环境配置 × 3
   共省下后人 ~24 小时踩坑时间 💪
   Top TL;DR:
   1. <tldr>
   2. <tldr>
   ```

---

## 失败降级

- lark 返回 `code 99991672` (缺 scope) → 告诉学生"权限不足,请 admin 检查 `bitable:app:readwrite`",停止流程。
- lark 返回 `code 1254xxx` (字段类型错) → LLM 自查 category 枚举值表,用严格中文枚举重试一次;仍失败则落 `context_md` 到 Doc 不落枚举字段。
- `data_layout` 返回 `tables.failure_archive` 为空 → 告诉学生"FailureArchive 表尚未初始化,请 admin 在 `src/bitable/schema.ts` 加 TableDef 后跑 `openclaw classmate setup-bitable`"。
- `feishu_create_doc` 失败 → 降级:仅写 bitable 行,`doc_url` 留空,提示学生"长文档建失败,内容已存在 context_md"。
