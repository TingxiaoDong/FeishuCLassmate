---
name: evolve-telemetry
description: |
  自我进化 Phase 1 — 工具遥测查询。每次 `feishu_classmate_*` 工具调用会自动
  写入 `ToolTrace` 多维表(由 index.ts 的 after_tool_call 钩子落表),本 skill
  告诉 agent 如何用原生 bitable 工具从这张表读出:周度工具使用统计、失败最多的
  工具、每个 skill 的成功率。

  **触发词**: "工具统计"、"这周用了多少工具"、"哪些工具在失败"、"成功率"、
  "tool trace"、"usage stats"、"telemetry"、"飞书同学干了什么"、
  "自我进化数据"、"Phase 2 可以进化什么了"。
---

# 自我进化遥测 Skill

## 前置:拿数据布局

```
feishu_classmate_data_layout()
  → { app_token, tables: { ..., tool_trace: { table_id } } }
```

`tables.tool_trace` 缺失 → 钩子空转,表里无数据。提示 admin 跑一次 `setup-bitable`。

## 场景 A:周度工具使用统计

用户: "这周飞书同学调了哪些工具,调了多少次?"

1. 计算本周起点 `weekStart` (周一 00:00 毫秒)
2. 拉本周所有 trace:
   ```
   feishu_bitable_app_table_record({ action:"list", table_id: <tool_trace>,
     filter: { conjunction:"and", conditions: [
       { field_name:"started_at", operator:"isGreater", value:["<weekStart>"] } ]},
     field_names: ["tool_name","ok","duration_ms","started_at"], page_size: 500 })
   ```
   返回 > 500 条 → page_token 翻页
3. 按 `tool_name` 分组计数 + 成功率 + 中位耗时,排序输出:
   ```
   ## 本周工具调用 (2026-W16, 共 N 次)
   - feishu_classmate_temi_speak — 42 次 (成功率 100%, p50 230ms)
   - feishu_classmate_supervision_start — 11 次 (91%, 45ms)
   ```

## 场景 B:找出最容易失败的工具

用户: "最近哪些工具在报错?"

1. 过滤 `ok=false` 近 7 天:
   ```
   filter: { conjunction:"and", conditions: [
     { field_name:"ok", operator:"is", value:["false"] },
     { field_name:"started_at", operator:"isGreater", value:["<now-7d ms>"] }] }
   ```
2. 按 `tool_name + error 前 120 字符` 分组聚合
3. 输出 Top 5 `(tool_name, error_prefix, count)`,附典型 `params_json` 片段
4. 失败率 > 30% 且 调用次数 ≥ 10 → 高亮标红,建议人工介入

## 场景 C:按 skill 算成功率

tool_name 前缀映射:

| 前缀 | skill |
|---|---|
| `feishu_classmate_temi_*` | [conduct-lab-tour](../conduct-lab-tour/SKILL.md) / [supervise-student](../supervise-student/SKILL.md) |
| `feishu_classmate_supervision_*` | [supervise-student](../supervise-student/SKILL.md) |
| `feishu_classmate_research_*` | [idle-research](../idle-research/SKILL.md) |
| `feishu_classmate_chat_*` | [initiate-conversation](../initiate-conversation/SKILL.md) |
| `feishu_classmate_data_layout` | (共用) |

1. 按上表把 trace 分桶
2. 每桶算 `ok / total` 作为该 skill 的"工具层成功率"
3. 输出:
   ```
   ## 本周各 Skill 工具层成功率
   - conduct-lab-tour: 94% (53 / 56)
   - supervise-student: 87% (47 / 54)
   ```
4. **不等于 skill 端到端成功率** — 单个 skill 里某次工具失败可能被降级兜住。附 caveat 告诉用户

## 场景 D:Phase 2 自我进化的输入

用户: "根据 ToolTrace 告诉我哪些 skill 可以进化了"

启发式输出建议:
1. **高失败率 skill** → 建议 agent 重读该 SKILL.md,补失败降级分支
2. **高耗时 tool** (p95 > 10s) → 建议异步化或加超时提醒
3. **从未被调用的 tool** → 可能 SKILL.md 没提到它 → 建议添加触发词或补用例
4. **params_json 出现相同错误模式** → 建议在 SKILL.md "字段枚举(严格)" 加反例

> 输出只是**建议**,不自动改别的 SKILL.md。Phase 2 完整实现才做自动改写,且一定要走人工 review。

## 需要新建的多维表

### ToolTrace

| 字段 | 类型 | 说明 |
|---|---|---|
| `trace_id` | Text (pk) | `tr_<ts>_<rand>` |
| `tool_name` | Text | e.g. `feishu_classmate_temi_speak` |
| `session_key` | Text | OpenClaw session key |
| `caller_open_id` | User | `[{id:"ou_xxx"}]` |
| `params_json` | Text | 工具入参 JSON,最长 8KB |
| `ok` | Checkbox | `true`=无错 |
| `error` | Text | ok=true 时为空串 |
| `duration_ms` | Number (0) | 毫秒 |
| `started_at` | DateTime | 毫秒 |

> 写入**不是本 skill 的事**。由 `index.ts` 的 `after_tool_call` 钩子 fire-and-forget 完成,失败会被吞掉只在 debug 日志留痕。

## 查询约束

- 永远**先过滤时间窗**再拉,`ToolTrace` 线性增长,全表 scan 很慢
- `page_size` ≤ 500,超过走翻页
- `params_json` 可能含敏感内容 → 输出给用户前只打印前 200 字符摘要,不原样复读
- 不要把 `caller_open_id` 明文贴给第三方,只用于后台聚合

## 失败降级

- `data_layout` 返回 `tool_trace` 为 undefined → 提示 admin 跑 setup,中止
- `code 99991672` (bitable 读权限不足) → 提示"Phase 1 遥测暂时只能在日志里看",中止
- 时间范围内 0 条 → 不要报错,正常输出"本周暂无工具调用记录"
