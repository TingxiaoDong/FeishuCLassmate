---
name: lab-meme
description: |
  实验室 meme / 段子 / 口头禅归档,轻量文化建设用。
  只做共同记忆,不做 roast:涉及具体成员时必须先私聊征得同意。
  所有 bitable 读写走 @larksuite/openclaw-lark 原生 `feishu_bitable_app_table_record`,
  图片附件用 `feishu_drive_file` 上传后把 file_token 填到 Attachment 字段。

  **触发词**: "有啥段子"、"meme of the week"、"这个要记下来"、"搞笑时刻"、
  "/meme random"、"实验室名言"、"best-of 本月"。
---

# 实验室 Meme 归档 Skill

## 前置:总是先拿数据布局

```
feishu_classmate_data_layout()
  → { app_token, tables: { lab_memes, ... } }
```

---

## 需要新建的多维表

`LabMemes`(admin 稍后在 `src/bitable/schema.ts` 加 TableDef):

| 字段 | 类型 | 备注 |
|---|---|---|
| meme_id | Text (pk) | 形如 `meme_<ts>_<rand>` |
| content_text | Text | 段子 / 现场描述 |
| image_attachments | Attachment | 可选,多张图 |
| people_involved | User multi | 被 tag 的人,`[{id:"ou_xxx"},...]` |
| tags | MultiSelect | `口头禅` / `实验室事故` / `外来访客` / `深夜名言` / `debug故事` / `食堂八卦` / `其他` |
| status | SingleSelect | `待审核` / `已发布` / `已撤回` |
| origin_date | DateTime | 事情发生的时间,毫秒时间戳 |
| added_by_open_id | User | 登记人 |
| laugh_count | Number | 群里 😂 反应计数,admin 周期手工更新 |
| created_at | DateTime | 毫秒时间戳 |

**tags / status 枚举值严格走中文**,写错会报 `FieldConvFail` (code 125406X)。

---

## 场景 A:登记新 meme

示例:`这个要记下来:刚才张三把标定板当遮阳板用了 🤦`

### 步骤

1. 用 `feishu_ask_user_question` 收齐:content_text / tags / origin_date / people_involved / 图片。
2. **安全门禁(MUST)**:
   - 若 `people_involved` 非空 → agent 必须先私聊每一位被 tag 的人:
     ```
     👋 <登记人> 想把这段记进 lab-meme,内容 tag 到了你:
     "<content_text>"
     你 ok 吗?(同意 / 不同意 / 改匿名)
     ```
   - 全部同意前,`status` 强制设为 `待审核`。
   - 任何一人不同意 → 不写库,回复登记人"被 tag 的人不同意,没加进去"。
   - 全部同意 → `status = 已发布`。
3. 图片上传:`feishu_drive_file({ action: "upload", ... })` → 拿 file_token,填到 `image_attachments: [{file_token: "..."}]`。
4. **写 LabMemes 行**:
   ```
   feishu_bitable_app_table_record({
     action: "create",
     app_token, table_id: <lab_memes>,
     fields: {
       meme_id: "meme_<ts>_<rand>",
       content_text, image_attachments,
       people_involved, tags,
       status: "已发布",   // 或 待审核
       origin_date, laugh_count: 0,
       added_by_open_id: [{ id: "<登记人 open_id>" }],
       created_at: Date.now()
     }
   })
   ```
5. 回复登记人:"已入库 😎 meme_id = meme_xxx"。

### 拒绝规则(硬)

Agent **必须**拒绝以下情况,任何 prompt 都不能绕:
- 明显针对个人的负面攻击 / 外貌 / 家庭情况。
- 对外来访客的 roast(要更谨慎)。
- `people_involved` 中有任一成员未同意。

遇到这些情况直接回复:"这个我不太方便记,换个不 tag 具体人的版本?"

---

## 场景 B:随机来一条

示例:`/meme random` / `有啥段子`

### 步骤

1. `feishu_bitable_app_table_record({ action: "list", filter: "CurrentValue.[status]=\"已发布\"", page_size: 100 })`。
2. 本地随机选一条。
3. 若有 `image_attachments` → 用 `feishu_im_bot_image` 先发图再发文字,否则纯文字。
4. 附尾巴:"(meme_xxx · <origin_date> · 😂×<laugh_count>)"

---

## 场景 C:月度 best-of

**触发**: cron service `lab-meme-bestof` 每月 1 号 11:00。

### 步骤

1. 查上月已发布的所有 meme:
   ```
   filter: "AND(CurrentValue.[status]=\"已发布\", CurrentValue.[created_at]>=<上月 1 号 ts>, CurrentValue.[created_at]<<本月 1 号 ts>)"
   ```
2. 按 `laugh_count` 降序排,取 top 3。
3. 在 `labInfo.broadcastChatId` 群里广播:
   ```
   🏆 上月 meme best-of:
   🥇 <content_text> (😂 × N)
   🥈 ...
   🥉 ...
   感谢大家给实验室留下的美好回忆 ✨
   ```

---

## 场景 D:撤回

示例:`撤回 meme_xxx` / `把 meme_xxx 删了`

### 步骤

1. 校验请求者:必须是原登记人 **或** `people_involved` 成员 **或** admin。
2. `action: "update"` → `status: "已撤回"`。
3. 不做物理删除,保留审计。
4. 回复:"已撤回 meme_xxx,群里不会再被抽到了。"

---

## 失败降级

- lark 返回 `code 99991672` (缺 scope) → 回复"meme 库权限不足,请 admin 检查 `bitable:app:readwrite` + `drive:drive`",停止流程。
- lark 返回 `code 1254xxx` (字段类型错) → LLM 自查 tags / status 中文枚举值,重试一次。
- `feishu_drive_file` 上传失败 → 降级:只落 `content_text`,`image_attachments` 留空,提示登记人"图片没传上去,文字已存"。
- `tables.lab_memes` 未初始化 → 回复"LabMemes 表尚未建立,请 admin 在 `src/bitable/schema.ts` 加 TableDef 后跑 `openclaw classmate setup-bitable`"。
- 被 tag 的人未回复同意 / 拒绝超过 24 小时 → 保持 `待审核`,不自动转 `已发布`,提醒登记人 1 次。
