---
name: reading-group
description: |
  实验室每周 reading group 轮值调度、论文选读、讨论归档。
  所有 bitable 操作走 @larksuite/openclaw-lark 的原生
  `feishu_bitable_app_table_record`,本 skill 只负责轮值算法、
  人机确认与群公告话术。

  **触发词**: "这周 reading group 谁讲"、"下周 reading group 安排"、
  "推荐这周读的 paper"、"RG 结束"、"past sessions"、"谁还没讲过"。
---

# Reading Group Skill

## 前置:总是先拿数据布局

```
feishu_classmate_data_layout()
  → { app_token, tables: { ..., reading_group, papers } }
```

所有 bitable 操作都用返回的 `app_token` + `tables.reading_group.table_id`。

---

## 需要新建的多维表

### ReadingGroup

| 字段 | 类型 | 说明 |
|---|---|---|
| session_id | Text (pk) | `rg_<ts>_<rand>` |
| date | DateTime | 本次 RG 的计划时间(毫秒) |
| presenter_open_id | User | 主讲人 |
| paper_id | Text | FK → `Papers.paper_id`(可为空,粘 arXiv 时再补;由 [manage-papers](../manage-papers/SKILL.md) 管理) |
| paper_title | Text | 论文题目 |
| paper_url | Url | arXiv / 期刊链接 |
| discussion_points_md | Text | 预生成的 3-5 个讨论问题(markdown) |
| actual_discussion_md | Text | 会后真实讨论纪要 |
| rating_avg | Number | 参会人打分平均(formatter `0.0`) |
| attendees | User (multi) | 参会人 |
| status | SingleSelect | `未开始` / `已准备` / `进行中` / `已结束` |

**中文枚举值强约束**:`status` 只能写 `未开始`、`已准备`、`进行中`、`已结束`。
写错会报 `FieldConvFail` (code 125406X)。

> 此表由管理员在 `skills/` 合流后统一建立,当前请先按 schema 写逻辑。

---

## 场景 A:每周轮值排班(cron 或手动触发)

**触发来源**:
- cron service `reading-group-rotate` 每周一 10:00 自动跑(本 skill 只描述,不负责实现 cron)
- 任意成员说 `下周 reading group 安排谁`

### 步骤

1. **读历史**:
   ```
   feishu_bitable_app_table_record({
     action: "list",
     app_token, table_id: <reading_group>,
     filter: "CurrentValue.[status]=\"已结束\"",
     sort: [{ field_name: "date", desc: true }]
   })
   ```
2. **算下一位主讲**(LLM 自己做):
   - 拉 `labInfo.members` 拿实验室全员 open_id 列表
   - 按每位成员 `presenter_open_id` 最近一次出现的 `date` 升序
   - 从未出现过的成员优先;最久没讲的排第一
3. **创建下周 session 行**(status=未开始):
   ```
   feishu_bitable_app_table_record({
     action: "create",
     fields: {
       session_id: "rg_<ts>_<rand>",
       date: <下周四 15:00 的毫秒>,
       presenter_open_id: [{ id: "<被选中的 open_id>" }],
       status: "未开始"
     }
   })
   ```
4. **DM 主讲**:"本周 RG 轮到你啦,请在周三前选一篇 paper 回复这条消息(arXiv 链接或 paper_id)"
5. 使用 `feishu_ask_user_question` 收集 paper 信息

---

## 场景 B:主讲选论文 → 生成讨论问题

示例: 主讲回复 `https://arxiv.org/abs/2501.12345` 或 `paper_id=p_xxx`

### 步骤

1. 若是 arXiv 链接 → 用 `feishu_classmate_research_search_works({ query: "<url 或 title>" })` 拉回 title/abstract/authors
2. 若是现有 `Papers` 表的 `paper_id` → 直接查 `Papers` 表拿字段
3. **LLM 基于 abstract 生成 3-5 条讨论问题**(不调工具),示例:
   - 方法的核心创新是什么?
   - 实验设置是否公平?baseline 覆盖充分吗?
   - 能在我们的 <机器人平台> 上复现吗?需要什么改动?
4. **回写 session 行**(status=已准备):
   ```
   action: "update",
   record_id: <上面 create 返回的>,
   fields: {
     paper_id, paper_title, paper_url,
     discussion_points_md: "1. ...\n2. ...",
     status: "已准备"
   }
   ```
5. **群公告**(通过 `labInfo.broadcastChatId` 发 text 消息):
   > 本周 RG:@<主讲> 讲《<paper_title>》,周四 3 点。
   > 预读问题:<discussion_points_md 前 3 条>
   > 链接:<paper_url>

---

## 场景 C:会后归档

触发:主讲或导师说 `RG 结束` / `reading group 完事了`。

### 步骤

1. 定位最近 `status=已准备` 或 `进行中` 的那行(sort date desc 取第一)
2. 用 `feishu_ask_user_question` 依次问:
   - 参会人是谁?(多选)
   - 1-5 分,大家给这篇 paper 打几分?(算平均)
   - 讨论纪要一段话
3. **更新行**:
   ```
   fields: {
     attendees: [{ id: "ou_a" }, ...],
     rating_avg: <平均分>,
     actual_discussion_md: "<纪要>",
     status: "已结束"
   }
   ```
4. 回复"已归档,辛苦啦 🙏"(此处是话术,不写入任何文件)

---

## 场景 D:查询

- **`最近几次 RG`**: filter `status="已结束"`, sort `date desc`, page_size 10 → 输出 `日期 | 主讲 | 题目 | 平均分`
- **`谁还没讲过`**: list 全部 `已结束`,按 `presenter_open_id` 统计,与 `labInfo.members` 求差集;讲过的按最久未讲排序

---

## 失败降级

- lark 返回 `code 99991672`(缺 scope)→ 告诉触发者"权限不足,请 admin",停止
- lark 返回 `code 1254xxx`(字段类型错)→ 对照上面枚举表自查,用正确中文值重试一次
- `data_layout` 无 `reading_group` 表 → 回复"`ReadingGroup` 表尚未创建,请管理员
  在 schema 合流后跑 setup",流程终止
- `feishu_classmate_research_search_works` 失败 → 直接用主讲粘贴的 title 填 `paper_title`,
  `discussion_points_md` 写"(abstract 获取失败,请主讲会前补问题)"
- 轮值算法拿不到 `labInfo.members` → 降级为问群主手动点名
