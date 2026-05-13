---
name: reserve-equipment
description: |
  学生预约 GPU / 3D 打印机 / 显微镜等共享设备的时段。
  逻辑：解析自然语言时间 → 查冲突 → 无冲突则写 `Reservations` 行并广播 → 有冲突则列出占位让学生改时间。
  所有数据操作走 @larksuite/openclaw-lark 的原生 `feishu_bitable_app_table_record`。
  本 skill 只做时间解析 / 冲突判定 / 交互确认。

  **触发词**: "预约 GPU"、"占 3D 打印机"、"占显微镜"、"订一下 GPU"、
  "reserve microscope tomorrow 2-5pm"、"book gpu0 tonight"、
  "/reserve …"、"今晚 GPU 还有人用吗"、"明天下午 3D 打印机空吗"。
---

# 设备预约 Skill

## 前置：总是先拿数据布局

```
feishu_classmate_data_layout()
  → { app_token, tables: { equipment, reservations, ... } }
```

后续所有 bitable 操作用 `app_token` + 对应 `table_id` 丢给 lark 原生工具。

---

## 字段枚举（严格）

| 字段 | 有效值 |
|---|---|
| status | `pending`、`confirmed`、`active`、`completed`、`cancelled` |

**Agent 必须严格用以上小写英文值**（与已有 `Equipment.state` 的中文枚举区分），
写错会返回 `FieldConvFail`（code 125406X）。

`Reservations` 表其它字段：`reservation_id` (Text primary)、`equipment_id` (Text, FK by string
到 Equipment.equipment_id)、`requester_open_id` (User)、`start_at` (DateTime ms)、`end_at`
(DateTime ms)、`purpose` (Text)、`created_at` (DateTime ms)。

---

## 场景 A：新建预约

示例: `预约 GPU0 明天下午 2 点到 5 点，跑 ablation`

### 步骤

1. **解析时间**（LLM 自己做，不调 tool）：
   `tomorrow 14:00 - 17:00` → `start_at_ms, end_at_ms`
   - 兜底：若解析失败 / 跨天不合理 → 用 `feishu_ask_user_question` 问 "从几点到几点"
   - 校验：`end_at > start_at` 且 `end_at - start_at <= 24h`，否则确认一次

2. **定位 equipment_id**：
   ```
   feishu_bitable_app_table_record({ action: "list", table_id: <equipment>,
     filter: "CurrentValue.[name].contains(\"GPU0\")",
     field_names: ["equipment_id","name","state"] })
   ```
   0 条 → "设备不存在"；多条 → 用 `feishu_ask_user_question` 让学生选；
   命中 `state=丢失/维修` → 拦截。

3. **冲突检测**（核心，公式：`existing.start < new.end AND existing.end > new.start`）：
   ```
   feishu_bitable_app_table_record({ action: "list", table_id: <reservations>,
     filter: "AND(
       CurrentValue.[equipment_id]=\"gpu0\",
       OR(CurrentValue.[status]=\"pending\", CurrentValue.[status]=\"confirmed\", CurrentValue.[status]=\"active\"),
       CurrentValue.[start_at]<<end_at_ms>>,
       CurrentValue.[end_at]>>start_at_ms)" })
   ```

4. **有冲突**：列出占位（`HH:MM-HH:MM @xxx (purpose)`），用 `feishu_ask_user_question` 问 "换时间 / 换设备 / 取消"。

5. **无冲突 → 写入 Reservations 行**：
   ```
   feishu_bitable_app_table_record({ action: "create", table_id: <reservations>, fields: {
     reservation_id: "res_<ts>_<rand>", equipment_id: "gpu0",
     requester_open_id: [{ id: "ou_xxx" }],
     start_at: <ms>, end_at: <ms>,
     purpose: "跑 ablation", status: "confirmed",
     created_at: Date.now() }})
   ```

6. **广播**：往 `labInfo.broadcastChatId` 群发 `📌 @xxx 已预约 GPU0 04-18 14:00-17:00（跑 ablation）`
7. 回学生：`✅ 预约成功 res_xxx，到点会提醒你`。

---

## 场景 B：查询即将到来的预约

示例: `今晚 GPU 还有人用吗？` / `明天 3D 打印机什么时候空？`

```
feishu_bitable_app_table_record({
  action: "list",
  filter: "AND(
    CurrentValue.[equipment_id]=\"gpu0\",
    CurrentValue.[start_at]>=<now_ms>,
    CurrentValue.[start_at]<<now_ms + 24*3600_000>>,
    OR(CurrentValue.[status]=\"pending\", CurrentValue.[status]=\"confirmed\", CurrentValue.[status]=\"active\")
  )",
  field_names: ["start_at","end_at","requester_open_id","purpose","status"],
  sort: [{ field_name: "start_at", desc: false }]
})
```

格式化：`🕒 HH:MM-HH:MM @xxx (purpose) [status]`，最多 10 条；若为空 → "未来 24h 没人预约 GPU0，随便用 🎉"。

---

## 场景 C：取消预约

示例: `取消 res_xxx` / `我那个 GPU 预约不用了`

1. `filter: "AND(CurrentValue.[reservation_id]=\"res_xxx\", CurrentValue.[requester_open_id]=[{\"id\":\"ou_xxx\"}])"`
   拿 record_id（仅本人可取消；若非本人 → 告诉学生 "只有发起人可取消"）
2. `action: "update"`, `fields: { status: "cancelled" }`（不删行，保留审计）
3. 回学生 `✅ 已取消`，并在广播群补一条 `🚫 @xxx 取消了 GPU0 xx-xx 的预约`

---

## 场景 D：到点提醒（cron，本期不实现，仅说明）

> **本 skill 不实现 cron**。由 `feishu-classmate` 的 cron service（见 cron 模块）扫 `Reservations`：
> - `start_at - 15min <= now < start_at AND status=confirmed` → DM requester "15 分钟后开始"
> - `now >= end_at AND status in (confirmed, active)` → 自动更新 `status=completed`
> Agent 侧只需保证字段枚举正确，cron 能跑。

---

## 失败降级

- 学生给的时间完全无法解析 → `feishu_ask_user_question` 让他改用 `YYYY-MM-DD HH:MM` 格式重发
- lark `code 99991672` (缺 scope) → "bitable 权限不足，请 admin 联系"，停止
- lark `code 125406X` (FieldConvFail) → 重点检查 `status` 是否用了严格的小写英文枚举、
  `start_at/end_at/created_at` 必须毫秒时间戳
- 冲突检测返回 > 0 条但 UI 层拉取失败 → **宁可拒写也不要跳过检测**，让学生重试
- 广播群发消息失败 → 不回滚预约，只提示学生 "预约已建，广播失败，可手动知会"
- `feishu_classmate_data_layout` 返回 `app_token` 为空 → "数据库未初始化，请运行 `openclaw classmate setup-bitable`"
- 同一学生短时间内连续提交完全重合的两条 → 把第二条视作重复提交，返回第一条的 reservation_id
