---
name: lab-onboarding
description: |
  新同学入职流程:一篇专属 Doc 承载 12 项 checklist,bot 每日跟进未完成项。
  所有 doc / drive 操作走 @larksuite/openclaw-lark 原生工具
  (`feishu_create_doc`, `feishu_update_doc`, `feishu_fetch_doc`,
  `feishu_ask_user_question`)。
  本 skill 只负责:checklist 编排、DM 提醒节奏、与 `manage-gantt` /
  `manage-equipment` 的跨 skill 跳转。

  **触发词**: "新同学来了"、"给 xxx onboarding"、"onboarding xxx"、
  新生在大群发自我介绍、导师 @bot 指定学生入职。
---

# 新生 Onboarding Skill

## 前置:拿数据布局

```
feishu_classmate_data_layout()
  → { app_token, docs: { publicProjects, privateProjects, researchReports,
                         dailyLogs, labArchive?, safetyManual? },
      labInfo: { name, broadcastChatId, ... } }
```

不新建 bitable 表;每个新生占一篇 Doc。

## 12 项 checklist(顺序固定)

| # | 项目 | 责任方 | 跨 skill |
|---|---|---|---|
| 1 | 加 bot 到个人飞书 + 进实验室大群 | 学生 | — |
| 2 | 拿到 docs 编辑权限(publicProjects / privateProjects / researchReports / dailyLogs) | 导师 | — |
| 3 | 在 Projects 表建第一行 | 学生 | `manage-gantt` |
| 4 | 读完实验室 safety manual | 学生 | — |
| 5 | 注册 GitHub org + 被加进 team | 学生 + 导师 | — |
| 6 | 账号开通:GPU 集群 SSH / VPN / Slack | Admin | — |
| 7 | 领设备:工位钥匙 + 门禁卡 | 学生 | `manage-equipment` |
| 8 | 选定研究方向 + 和导师 1:1 | 导师 | — |
| 9 | 读 3 篇入门 paper | 学生 | `idle-research` / `manage-papers` |
| 10 | 跑通第一个项目 baseline | 学生 | — |
| 11 | 参加第一次组会 + 自我介绍 | 学生 | — |
| 12 | 资料入 Wiki + 大群欢迎 | bot | — |

---

## 流程

### 步骤 1:触发 & 抽取

导师消息 `给 张三 onboarding`:
1. LLM 抽出学生名 / `@` open_id / 起始日期(默认今天 `YYYYMMDD`)
2. `feishu_ask_user_question` 向导师确认:学生 open_id、导师 open_id、是否"保密项目组"

### 步骤 2:创建专属 Doc

```
feishu_create_doc({
  title: "onboarding-张三-20260417",
  folder_token: <docs.researchReports 同级或专属 onboarding folder>,
  content_md: <下面的模板>
})
  → { doc_token, url }
```

Doc 内容模板(12 个 checkbox):

```
# 张三 入职 checklist

- [ ] 1. 加 bot 到个人飞书 + 进实验室大群
- [ ] 2. 拿到 docs 编辑权限(4 个核心 Doc)
- [ ] 3. 在 Projects 表建第一行
- [ ] 4. 读完实验室 safety manual
- [ ] 5. 注册 GitHub org + 加 team
- [ ] 6. 账号开通:GPU SSH / VPN / Slack
- [ ] 7. 领工位钥匙 + 门禁卡
- [ ] 8. 和导师 1:1 敲定研究方向
- [ ] 9. 读 3 篇入门 paper
- [ ] 10. 跑通第一个项目 baseline
- [ ] 11. 参加第一次组会 + 自我介绍
- [ ] 12. 完成!
```

### 步骤 3:首次 DM 推送

DM 学生:
- 欢迎语 + Doc URL
- 前 3 项的详细指引(link 到 safety manual、导师名 & open_id 等)

### 步骤 4:每日跟进(前 5 天)

每天 10:00(cron `onboarding-nudge`,未实装,此处声明契约):
1. `feishu_fetch_doc({ doc_token })` 解析 checkbox 勾选状态
2. 找到第一个未勾选项 → DM 学生,给具体指引;跨 skill 的跳转直接引导:
   - 第 3 项未完 → `@bot 帮我建个 project`(落入 `manage-gantt`)
   - 第 7 项未完 → `@bot 借工位钥匙`(落入 `manage-equipment`)
   - 第 9 项未完 → `@bot 推 3 篇入门 paper`(落入 `idle-research`)
3. 更新 Doc:追加"最后提醒:YYYY-MM-DD HH:mm"一行(用 `feishu_update_doc` append)

### 步骤 5:超时升级

如果第 5 天后仍有未完成:
1. DM 导师:"张三 onboarding 第 N 项拖了 5 天,辛苦看一下"
2. 学生端停止每日 DM,改为每 3 天一次

### 步骤 6:完成收尾

当 12 项全部勾选(或第 12 项手动勾选即视为完成):
1. `feishu_im_bot_image`(或文本)在 `labInfo.broadcastChatId` 发: `@all 欢迎 张三 加入 <labInfo.name>!🎉`
2. 如果配置了 `docs.labArchive`:把 onboarding Doc move 到 archive folder(通过 `feishu_update_doc` 改 parent,或 drive 工具)
3. 给导师发一条总结:开始日 / 完成日 / 用时几天

---

## 枚举值(严格)

| 概念 | 有效值 |
|---|---|
| checklist 项状态 | `未开始`、`进行中`、`完成`(内部用,不落表,仅 Doc checkbox) |
| 完成度判定 | Doc 中 `- [x]` 的行数 / 12 |

---

## 失败降级

- `docs.researchReports` folder 未配置 → 用 drive 根目录创建 Doc,warning 提示导师"建议配置 onboarding folder"
- `feishu_create_doc` 返回 `99991672`(缺 scope) → 回退到纯 DM 模式:把 12 项一次性发给学生,不再每日跟进
- `feishu_fetch_doc` 读不到(学生手动删了) → DM 学生:"Doc 不见了,要不要重建?"
- 学生未加 bot(步骤 1 做不了) → 导师代为转发第一条 DM,stay 在"等待步骤 1"直到能联系到学生
- `labInfo.broadcastChatId` 未配 → 步骤 6 的欢迎改发到导师私聊,让导师手动转
