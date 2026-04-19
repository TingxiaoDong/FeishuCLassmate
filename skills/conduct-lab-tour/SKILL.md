---
name: conduct-lab-tour
description: |
  当用户请求带访客参观实验室时使用。按 5 个阶段(开场白 → 实验室基本信息 →
  特色实验区域 → 工位区 → 问答)推进,全程协调 Temi 走位 + TTS + 视觉识别。

  **触发词**: "带参观"、"带我参观"、"tour"、"导览"、"introduce the lab"、
  "来人了"、"有访客"。

  **当以下情况时使用**:
  (1) 有人请求参观或介绍实验室
  (2) 访客到达,被带到实验室门口
  (3) 需要生成对外讲解词
---

# 导览 Skill

## 前置:拿数据布局

```
feishu_classmate_data_layout()
  → { app_token, tables: { projects, ... },
      docs: { publicProjects }, labInfo: { name, supervisorName, memberCount, specialAreas } }
```

- `feishu_classmate_temi_status` 必须返回 `connected=true`(非 mock 模式)
- Temi 不可用或 `mockMode=true` → 降级为**纯文字导览**(飞书群/私信输出讲解词,不调 temi_*)
- 必须能读到【可公开项目】Doc,没有则提示管理员配 `docs.publicProjects`

## 5 阶段剧本

### 阶段 1:开场白(在入口)

1. `feishu_classmate_temi_navigate_to({ location: "入口" })`
2. `feishu_classmate_temi_detect_person({ timeout_ms: 3000 })` — 获取访客 open_id(若 lab 成员)
3. 调用 LLM 生成欢迎词,例如:
   > "欢迎来到 {labInfo.name},我是飞书同学,身兼数职,也负责带人参观。今天由我带您转转。"
4. `feishu_classmate_temi_speak({ text: <欢迎词> })`

### 阶段 2:实验室基本信息

1. 读取【可公开项目】Doc (`docs.publicProjects`),取最近 3 个项目的 title + abstract
2. 生成讲解词,必须包含:
   - 研究方向摘要
   - 导师姓名 `{labInfo.supervisorName}`
   - 成员人数 `{labInfo.memberCount}` + "我这个特殊的成员"
   - 最近研究项目亮点
   - **提示访客**: "如果您多来几次,听到的内容可能会不一样 — 因为同学们会把项目进度交给我记录"
3. `feishu_classmate_temi_speak`

### 阶段 3:特色实验区域

遍历 `{labInfo.specialAreas}`:

1. `feishu_classmate_temi_navigate_to({ location: <area.name> })`
2. `feishu_classmate_temi_speak({ text: <area.narration> })`
3. 可选:在"生活仿真区"这种有故事的地方,补一句"我也在这里训练过"

### 阶段 4:工位区

1. `feishu_classmate_temi_navigate_to({ location: "工位区" })`
2. `feishu_classmate_temi_detect_person()` — 识别画面中的学生 open_id
3. 如果识别到 `open_id`:
   - 用 `feishu_bitable_app_table_record` action=list 查 Projects
     (由 [manage-gantt](../manage-gantt/SKILL.md) 管理),
     filter = `CurrentValue.[owner_open_id]=[{id:"<open_id>"}]` + `visibility="可公开"`,
     取 `title`
   - 生成讲解词: "这位 {学生} 正在做 {project_title}"
4. `feishu_classmate_temi_speak`

### 阶段 5:问答

1. 切换到 RAG 模式:system prompt 追加【可公开项目】Doc 内容
2. 回到入口 `feishu_classmate_temi_navigate_to({ location: "入口" })`
3. `feishu_classmate_temi_speak({ text: "参观到这里就差不多了,有问题可以问我" })`
4. 进入问答循环,任何问题都用【可公开项目】做 RAG
5. 退出条件:访客说"谢谢"、"结束"、"bye" 或 3 分钟无提问

## 安全约束

- Temi 最大速度 0.5 m/s(由 sidecar 强制)
- 全程开启碰撞检测,任何时刻收到 "停" / "stop" / "暂停" → `feishu_classmate_temi_stop({ immediate: true })`
- 不得讲【保密项目】里的任何内容
- 识别到的 open_id **不得在飞书消息中明文暴露**,只用于后台查询

## 失败降级

| 情况 | 降级 |
|---|---|
| Temi 离线 | 走纯文字版,在飞书群里把各阶段讲解词依次发出 |
| 【可公开项目】Doc 未配置 | 跳过阶段 2、4 中的项目信息,只讲通用模板 |
| 阶段 4 未识别到学生 | 用通用讲解词 "这里是同学们的工位..." |

## 事后动作

- 把本次导览摘要(访客时间、走过的地点)写入【日常记录】Doc
