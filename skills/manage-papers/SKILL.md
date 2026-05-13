---
name: manage-papers
description: |
  当学生需要收录一篇论文(arXiv / DOI / 手动录入)到 Papers 表、查询组里读过/在读的 paper、
  或把一篇 paper 挂到某个 Project 下时使用。
  所有数据操作走 @larksuite/openclaw-lark 的原生 `feishu_bitable_app_table_record`,
  arXiv 元数据抓取走 `feishu_classmate_research_search_works`。
  本 skill 只做流程编排 / 交互 / 去重。

  **触发词**: "存这篇 paper"、"帮我收录一下"、"收一下这篇"、"paper add"、"/paper add"、
  "这篇值得读"、"把这个 arxiv 存一下"、DOI/arXiv 链接直接粘贴进来、
  "帮我查关于 XX 的 paper"、"我们组读过 XX 吗"。
---

# 论文管理 Skill

## 前置:总是先拿数据布局

```
feishu_classmate_data_layout()
  → { app_token, tables: { projects, gantt, equipment, research, papers, ... } }
```

后续所有 bitable 操作用 `app_token` + `tables.papers.table_id` 丢给 lark 的原生工具。

---

## 字段枚举(严格)

| 字段 | 有效值 |
|---|---|
| read_status | `待读`、`在读`、`已读`、`引用` |

**Agent 必须严格用以上中文值**,写错会报 `FieldConvFail` (code 125406X)。

Papers 表其它字段:`paper_id` (Text primary)、`title`、`authors` (逗号分隔)、`venue`、
`year` (Number)、`doi` (Url)、`arxiv_id` (Text)、`abstract`、`keywords` (MultiSelect, 动态追加)、
`notes`、`shared_by_open_id` (User)、`added_at` (DateTime, 毫秒时间戳)。

---

## 场景 A:学生粘贴 arXiv 链接 / ID 收录

示例消息: `帮我存下这篇 https://arxiv.org/abs/2501.12345` 或 `/paper add 2501.12345`

### 步骤

1. 从消息里解析出 `arxiv_id`(支持 `arxiv.org/abs/XXX`、`arxiv.org/pdf/XXX`、裸 ID)
2. **去重**: 先 `feishu_bitable_app_table_record`
   ```
   action: "list"
   filter: "CurrentValue.[arxiv_id]=\"2501.12345\""
   ```
   如果命中 → 告诉学生"已经收录过了,record_id=…",展示现有 title/read_status,停止创建
3. 抓元数据:
   ```
   feishu_classmate_research_search_works({ topic: "arxiv_id:2501.12345", limit: 1 })
   ```
   拿到 `{ title, url, abstract, year }`。若 `works` 为空 → 降级到场景 C(手动)
4. 用 `feishu_ask_user_question` 确认/补全: title、year、authors、keywords (2-5 个)
5. `feishu_bitable_app_table_record`
   ```
   action: "create"
   table_id: <papers>
   fields: {
     paper_id: "paper_<timestamp>_<rand>",
     title, authors, venue: "arXiv",
     year,
     doi: null,
     arxiv_id: "2501.12345",
     abstract, keywords,
     read_status: "待读",
     shared_by_open_id: [{ id: "<学生 open_id>" }],
     added_at: Date.now()
   }
   ```
6. 回学生"已收录 ✅ [标题](url)"并附带 `record_id`

---

## 场景 B:粘贴 DOI 收录

示例: `存这篇 doi:10.1145/3580305.3599123`

### 步骤

1. 解析 `doi` 字符串
2. 去重: `filter: "CurrentValue.[doi]=\"10.1145/...\""`(doi 字段是 Url,比对 link 里的 text)
3. **DOI 元数据抓取目前不支持自动化** — 告诉学生:
   > DOI 元数据暂未实现自动抓取,请手动粘贴 title / authors / venue / year。
4. 用 `feishu_ask_user_question` 拿 title/authors/venue/year/keywords
5. 同场景 A 步骤 5 写入,区别:`arxiv_id: ""`、`doi: { link: "https://doi.org/10.1145/...", text: "10.1145/..." }`、`venue: <期刊/会议名>`

---

## 场景 C:完全手动录入(降级路径)

触发:arXiv 抓取失败 / 没给链接只给书名。

1. `feishu_ask_user_question` 依次收集 title → authors → venue → year → keywords → abstract(可跳过)
2. 同场景 A 步骤 5 写入 `Papers`,arxiv_id 和 doi 都留空

---

## 场景 D:挂到某个 Project (由 [manage-gantt](../manage-gantt/SKILL.md) 管理)

学生补一句 `这篇跟 proj_xxx 相关` 或在收录时说 `存到 RLHF-Agent 项目下`。

1. 查 Projects:`filter: "CurrentValue.[project_id]=\"proj_xxx\""` 或按 title 模糊
2. 取现有 `Projects` 行的 `record_id`
3. 方案 A(简单): `action: "update"` 把该 project 行的 `notes`/`abstract_doc_token` 追一条论文链接
4. 方案 B(推荐后续做): 新建 `ProjectPaper` 关联表 — **本期先不做**,用方案 A

---

## 场景 E:查询已收录论文

示例: `帮我查关于 RLHF 的 paper`、`我们组读过 diffusion 的吗`

```
feishu_bitable_app_table_record({
  action: "list",
  filter: "OR(CurrentValue.[title].contains(\"RLHF\"), CurrentValue.[keywords].contains(\"RLHF\"))",
  field_names: ["paper_id","title","year","read_status","shared_by_open_id"]
})
```

格式化: 按 `year` 倒序,最多 10 条,每行 `📄 [title] ({year}, {read_status}) — shared by @xxx`。

---

## 场景 F:更新阅读状态

学生说 `paper_xxx 我读完了` / `把那篇标成已读`。

1. `filter: "CurrentValue.[paper_id]=\"paper_xxx\""` 拿 record_id
2. `action: "update"`, `fields: { read_status: "已读", notes: "<读后感,可选>" }`

---

## 失败降级

- `feishu_classmate_research_search_works` 返回 `works: []` → 进场景 C(手动录入),不要阻塞用户
- lark `code 99991672` (缺 scope) → 告诉学生 "bitable 权限不足,请 admin 联系",停止
- lark `code 1254068` (Url 字段转换失败) → `doi` 字段必须是 `{link, text}` 对象,不是纯字符串;重试一次
- lark `code 125406X` (FieldConvFail) → 重点检查 `read_status` 是否用了严格枚举、`added_at` 是否毫秒
- `feishu_classmate_data_layout` 返回 `app_token` 为空 → "数据库未初始化,请运行 `openclaw classmate setup-bitable`"
- 去重查询返回超过 1 条 (arxiv_id 冲突) → 数据异常,不自动处理,把所有命中行展示给学生让他决定
