---
name: submission-tracking
description: |
  跟踪论文投稿生命周期:投稿 → 审稿 → 决定 → 接收/被拒。
  所有 bitable 操作走 @larksuite/openclaw-lark 原生 `feishu_bitable_app_table_record`。
  本 skill 只负责:自然语言状态识别、状态机约束、群内祝贺/催促。

  **触发词**: "我投稿了一篇 xxx"、"paper submitted"、"xxx 送审了"、
  "xxx 给了 major revision"、"revision back"、"xxx 被接收了"、"xxx 被拒了"、
  "status update xxx"、"list submissions"、"看下投稿状态"。
---

# 论文投稿跟踪 Skill

## 前置:拿数据布局

```
feishu_classmate_data_layout()
```

用 `tables.submissions.table_id` + `app_token` 对 `Submissions` 表操作。

## 枚举值(严格)

| 字段 | 有效值 |
|---|---|
| status | `准备中`、`已投`、`审稿中`、`major revision`、`minor revision`、`已接收`、`被拒`、`已撤回` |

写错 lark 返回 `code 1254061`,agent 必须用以上精确中文/英文值。

### 合法状态转移

```
准备中 → 已投 → 审稿中 → { major revision | minor revision | 已接收 | 被拒 }
major/minor revision → 审稿中 → 已接收 | 被拒
任意状态 → 已撤回
```

非法转移(如 `被拒 → 审稿中`)要先 `feishu_ask_user_question` 确认是否重投/撤销。

---

## 场景 A:新建投稿

示例: `我投稿了一篇 "XXX 算法" 到 NeurIPS 2026,决定 deadline 9-20`

### 步骤

1. LLM 抽字段: `title`、`venue`、`decision_due`(解析为毫秒)、`author_open_ids`(默认发消息者)、`paper_id`(可选,FK 到 Papers,由 [manage-papers](../manage-papers/SKILL.md) 管理)
2. 用 `feishu_ask_user_question` 回读确认:标题 / venue / 决定 deadline / 作者列表
3. 创建:
   ```
   feishu_bitable_app_table_record({
     action: "create",
     app_token, table_id: <submissions>,
     fields: {
       submission_id: "sub_<timestamp>_<rand>",
       paper_id: "<对应 Papers 表 id 或空串>",
       title: "<title>",
       venue: "<venue>",
       author_open_ids: [{ id: "<open_id>" }, ...],
       status: "已投",
       submitted_at: <Date.now()>,
       decision_due: <毫秒>,
       notes: ""
     }
   })
   ```
4. 回复 "已登记" + 鼓励一句

---

## 场景 B:状态更新

示例: `XXX 给了 major revision` / `那篇 NeurIPS 被接收了!`

### 步骤

1. LLM 识别 submission(按 title 模糊匹配 `venue`/`title`):
   ```
   feishu_bitable_app_table_record({
     action: "list",
     filter: "OR(CurrentValue.[title].contains(\"XXX\"), CurrentValue.[venue]=\"NeurIPS\")"
   })
   ```
2. 唯一匹配 → 直接更新。多个 → `feishu_ask_user_question` 让用户选。
3. 更新字段:
   - `major/minor revision` → `status=major revision`(或 minor),`decision_at=Date.now()`
   - `已接收` → `status=已接收`,`decision_at=Date.now()`
   - `被拒` → `status=被拒`,`decision_at=Date.now()`
4. 若 `status=已接收`:在 `labInfo.broadcastChatId` 群里发 `🎉 恭喜 @xxx!论文《title》被 venue 接收!`
5. 若 `status=被拒`:只发 DM,不广播,附一句鼓励

---

## 场景 C:列表查询

示例: `list submissions` / `看下投稿状态`

1. `action: "list"`,按 `status` 分组
2. 输出紧凑表格(按 venue 排序,逾期未决标 ⚠️):

```
## 审稿中 (3)
| 标题 | venue | 投稿日 | 距决定 |
|---|---|---|---|
| ... | NeurIPS 2026 | 2026-03-01 | 14d |

## Major revision (1)
...
## 已接收 (2)
...
```

---

## 场景 D:超期未响应催促(cron 占位)

cron `submission-followup` 每周一 10:00(未实装;此处只声明契约):

1. `action: "list", filter: "AND(CurrentValue.[status]=\"已投\", CurrentValue.[submitted_at]<" + (Date.now() - 30*86400_000) + ")"`
2. 每条给 `author_open_ids[0]` 发私聊:"你的投稿《title》已 N 天未更新,要不要联系 PC chair?"
3. 如果 `decision_due` 也过了,抄送导师

---

## 失败降级

- lark 返回 `code 99991672`(缺 scope) → 告诉用户"权限不足,请 admin"
- lark 返回 `code 125406x`(字段错) → 自查本页枚举表,修正后重试一次
- 状态机非法转移 → `feishu_ask_user_question` 强制二次确认;若用户坚持则加 `notes: "manual override"` 后更新
- 模糊匹配 0 条 → 提示用户"没找到对应投稿,要不要新建?"
- `data_layout` 的 `submissions` 表缺失 → 告诉用户"先跑 `openclaw classmate setup-bitable`"
