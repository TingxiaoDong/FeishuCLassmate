---
name: manage-equipment
description: |
  实验室器材借用、归还、查询与资产巡查。
  所有 bitable 操作走 @larksuite/openclaw-lark 的 `feishu_bitable_app_table_record` 直接调用。
  本 skill 只做对话编排和业务规则校验。

  **触发词**: "借 xxx"、"借用"、"还 xxx"、"归还"、"xxx 在哪里"、
  "还有几个 xxx"、"报丢"、"资产检查"。
---

# 器材管理 Skill

## 前置:拿数据布局

```
feishu_classmate_data_layout()
```

后面所有对 `Equipment` 表的操作,用 `tables.equipment.table_id` + `app_token`。

## 字段枚举(严格)

| 字段 | 有效值 |
|---|---|
| state | `在库`、`借出`、`维修`、`丢失` |

---

## 场景 A:借用登记

示例用户消息: `借示波器 3 天`

### 步骤

1. **查候选器材**
   ```
   feishu_bitable_app_table_record({
     action: "list",
     app_token, table_id: <equipment>,
     filter: "AND(CurrentValue.[name].contains(\"示波器\"), CurrentValue.[state]=\"在库\")"
   })
   ```
2. 若 0 条在库 → 告诉学生"没有可用的示波器"
3. 若多条 → 用 `feishu_ask_user_question` 让学生选
4. **计算 expected_return 毫秒时间戳**:
   - "3 天" → `Date.now() + 3*86400_000`
   - "下周五" → LLM 解析
5. **更新 Equipment 行**(注意 record_id 从步骤 1 取):
   ```
   feishu_bitable_app_table_record({
     action: "update",
     app_token, table_id: <equipment>,
     record_id: <选中那条>,
     fields: {
       state: "借出",
       borrower_open_id: [{ id: "<学生 open_id>" }],
       borrow_at: Date.now(),
       expected_return: <毫秒>,
       notes: "<借用备注,可选>"
     }
   })
   ```
6. 回复学生 "已登记" + 在 labInfo.broadcastChatId 群里简短广播(用 lark 的 `feishu_im_bot_image` 或直接 text 消息)

### 校验

- **禁止重复借出**:步骤 1 过滤了 `state=在库`,如果换了别的过滤,执行前必须再核对
- **借用期限** > 30 天 → 提示学生再次确认

---

## 场景 B:归还登记

示例: `还 示波器` / `归还 热像仪`

### 步骤

1. 查学生正在借的:
   ```
   filter: "AND(CurrentValue.[name]=\"热像仪\", CurrentValue.[borrower_open_id]=[{\"id\":\"ou_xxx\"}])"
   ```
2. 找不到 → 告诉学生"你没有借用这台热像仪"
3. 判断是否逾期:`expected_return` < `Date.now()`
4. **更新**:
   ```
   fields: {
     state: "在库",          // 或 "维修"(学生说损坏)
     borrower_open_id: [],   // 清空
     borrow_at: null,
     expected_return: null,
     last_seen_at: Date.now()
   }
   ```
5. 回复 + 广播群

---

## 场景 C:库存查询

示例: `还有几个示波器?`

```
feishu_bitable_app_table_record({
  action: "list",
  filter: "CurrentValue.[name]=\"示波器\"",
  field_names: ["name","state","location","borrower_open_id"]
})
```

格式化输出简洁表格(3-5 行以内)。

---

## 场景 D:每日资产巡查(需要 Temi)

**触发**: cron service `equipment-patrol` 自动触发;mock 模式下跳过

### 步骤

1. `feishu_classmate_temi_rfid_scan_route({ route: [...] })` 获取扫描结果
2. `feishu_bitable_app_table_record({ action: "list", filter: "CurrentValue.[state]=\"在库\"" })` 拿当前在库清单
3. 差集对比,找出:
   - missing:表里在库但没扫到
   - moved:位置变化
   - unknown:扫到但不在表里
4. `batch_update` 更新 `last_seen_at` / `location`
5. 在广播群发摘要
