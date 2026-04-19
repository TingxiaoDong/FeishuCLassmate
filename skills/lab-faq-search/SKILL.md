---
name: lab-faq-search
description: |
  实验室 FAQ 搜索机器人:对新同学常见的"环境/docker/驱动/SSH/VPN/飞书配置"
  类问题秒回标准答案,查不到时再 fallback 到 mentor-dispatch。
  所有 bitable 读写走 @larksuite/openclaw-lark 原生 `feishu_bitable_app_table_record`,
  相关文档链接用 `feishu_search_doc_wiki` 补充,云盘附件用 `feishu_drive_file`。

  **触发词**: 学生消息以 "请问"、"请教"、"how do I"、"怎么"、"为什么" 起头,
  或关键词包含 "docker 装不上"、"ROS noetic 报错"、"conda"、"cuda mismatch"、
  "ssh 连不上"、"VPN"、"飞书配置"。
---

# 实验室 FAQ 搜索 Skill

## 前置:总是先拿数据布局

```
feishu_classmate_data_layout()
  → { app_token, tables: { lab_faq, mentor_answers?, ... } }
```

`mentor_answers` 可能缺席(mentor-dispatch 未启用时),代码里必须判空。

---

## 需要新建的多维表

`LabFAQ`(admin 稍后在 `src/bitable/schema.ts` 加 TableDef):

| 字段 | 类型 | 备注 |
|---|---|---|
| faq_id | Text (pk) | 形如 `faq_<ts>_<rand>` |
| question | Text | 标准问题,如 "Docker 权限不足怎么办" |
| answer_md | Text long | markdown 答案 |
| category | SingleSelect | `环境配置` / `Python包` / `Docker` / `GPU驱动` / `SSH连接` / `VPN` / `飞书配置` / `硬件故障` / `其他` |
| difficulty | SingleSelect | `新手` / `中级` / `高级` |
| tags | MultiSelect | 如 `cuda`、`conda`、`ros-noetic` |
| related_doc_urls | Text | 逗号分隔飞书 wiki/doc 链接 |
| helpful_count | Number | 累计有用次数 |
| last_verified_at | DateTime | admin 最近确认仍然有效的时间 |
| added_by_open_id | User | 登记人 |
| created_at | DateTime | 毫秒时间戳 |

**枚举值严格走中文**,写错会报 `FieldConvFail` (code 125406X)。

---

## 场景 A:学生问问题

示例:`请问 docker: permission denied while trying to connect 怎么办?`

### 步骤

1. LLM 抽关键词 → `["docker","permission","denied"]` + 推测 category = `Docker`。
2. **查 LabFAQ**:
   ```
   feishu_bitable_app_table_record({
     action: "list",
     app_token, table_id: <lab_faq>,
     filter: "OR(CurrentValue.[question].contains(\"docker\"), CurrentValue.[tags].contains(\"docker\"))"
   })
   ```
3. **若 `mentor_answers` 存在**再查一次同样 filter(表名换)。
4. 本地计算相似度(LLM 做),取 top 候选。
5. 阈值判定:
   - 若 top1 相似度高 → 直接回答 + 引用出处:
     ```
     💡 LabFAQ #faq_xxx (已被 12 人标记有用,2026-03-12 最近 verify)
     
     <answer_md 渲染>
     
     相关文档: <doc_url>
     ```
     同时增加 `helpful_count += 1`(`action: "update"`)。
   - 若相似度中等 → 列出 2-3 条候选,问学生"哪条更像你的问题"。
   - 若无命中 → 进入场景 B。

---

## 场景 B:没有命中时

1. 回复学生:"我这边没有现成答案,建议转师兄师姐,同时我先把这个问题记着。"
2. 调 [mentor-dispatch](../mentor-dispatch/SKILL.md) skill(如启用)。
3. 等师兄师姐回答后,问学生:
   > 这是一个新问题,师兄说的方案看起来有效,我可以帮你加到 FAQ 吗?
4. 学生确认后(走场景 C)。

---

## 场景 C:新增 FAQ 条目

### 步骤

1. 用 `feishu_ask_user_question` 把字段走一遍:question / answer_md / category / difficulty / tags / related_doc_urls。
2. 长答案用 `feishu_search_doc_wiki` 查找现有 wiki,把匹配的链接预填进 `related_doc_urls`。
3. **写 LabFAQ 行**:
   ```
   feishu_bitable_app_table_record({
     action: "create",
     fields: {
       faq_id: "faq_<ts>_<rand>",
       question, answer_md,
       category, difficulty, tags,
       related_doc_urls,
       helpful_count: 0,
       last_verified_at: Date.now(),
       added_by_open_id: [{ id: "<学生 open_id>" }],
       created_at: Date.now()
     }
   })
   ```
4. 回复学生:"已加入 FAQ 📚,下次有人问就不用麻烦师兄了。"

---

## 场景 D:月度陈旧条目提醒

**触发**: cron service `lab-faq-stale-check` 每月 1 号 10:00。

1. `feishu_bitable_app_table_record({ action: "list", filter: "CurrentValue.[last_verified_at] < <now - 90 天 ts>" })`,取最旧 5 条。
2. 私聊 admin:
   ```
   📚 这 5 条 FAQ 超过 90 天没有 verify,麻烦抽空确认一下是否仍然准确:
   - faq_xxx: Docker 权限不足怎么办 (last_verified 2025-11-02)
   - ...
   ```
3. admin 回复"已确认 faq_xxx" → 更新 `last_verified_at = Date.now()`。

---

## 失败降级

- lark 返回 `code 99991672` (缺 scope) → 回复"FAQ 查询权限不足,请 admin 检查 `bitable:app:readwrite`"。
- `tables.lab_faq` 未初始化 → 回复"LabFAQ 表尚未建立,请 admin 在 `src/bitable/schema.ts` 加 TableDef 后跑 `openclaw classmate setup-bitable`";仍然可以走 mentor-dispatch fallback。
- `tables.mentor_answers` 缺席 → 跳过 mentor_answers 查询,不阻塞主流程。
- `feishu_search_doc_wiki` 超时 → 忽略,related_doc_urls 留空即可。
