# PDF 合规审计 — 飞书同学

**对照源**: `/Users/haonianji/claudecode/feishutest/飞书同学.pdf`
**审计时间**: 2026-04-17
**SKILL 根目录**: `/Users/haonianji/claudecode/feishutest/feishu-classmate/skills/`

图例: ✅ 已覆盖 · 🟡 部分覆盖(有 gap) · ❌ 未实现

---

## 模块 1:导览(5 阶段剧本)

对照 PDF 第 4 页表格。

| PDF 条目 | 状态 | 依据 / Gap |
|---|---|---|
| 阶段 1 开场白 — 入口迎接、摄像头识别来宾 | ✅ 已覆盖 | [`conduct-lab-tour/SKILL.md` §阶段 1](../skills/conduct-lab-tour/SKILL.md) — `temi_navigate_to` + `temi_detect_person` + TTS 欢迎词 |
| 阶段 2 基本信息 — 研究方向/导师/成员/最近项目,结合【可公开项目】Doc 灵活更新 | ✅ 已覆盖 | [`conduct-lab-tour/SKILL.md` §阶段 2](../skills/conduct-lab-tour/SKILL.md) — 读 `docs.publicProjects`,拼进讲解词 |
| 阶段 3 特色实验区域 — 用动作/表情讲解 | 🟡 部分 | 讲解词有,但 PDF 提到"动作、表情";当前只调 `temi_speak`,未调用独立的 gesture/expression 工具。supervise-student 引用了 `temi_gesture`,但 tour skill 里没用 |
| 阶段 4 工位区 — 识别学生并调项目介绍 | ✅ 已覆盖 | [`conduct-lab-tour/SKILL.md` §阶段 4](../skills/conduct-lab-tour/SKILL.md) — `temi_detect_person` → lark bitable list Projects by owner_open_id |
| 阶段 5 问答 — RAG【可公开项目】 | ✅ 已覆盖 | [`conduct-lab-tour/SKILL.md` §阶段 5](../skills/conduct-lab-tour/SKILL.md) — RAG mode + 退出条件 |
| PDF 脚注"后台在导览提示词中预设好的,可手动更改" | 🟡 部分 | 当前依赖 `labInfo.specialAreas` 配置,支持手改,但没有专门的后台 CRUD 面板或 skill |

---

## 模块 2:器材管理

对照 PDF 第 5 页。

### 资产检查(每日巡查)

| PDF 条目 | 状态 | 依据 / Gap |
|---|---|---|
| 每日开机后自动运行 | ✅ 已覆盖 | `services/equipment-patrol.ts` cron,默认 `30 8 * * *`(config.ts) |
| RFID 识别 + 视觉确认位置,记录到文档 | ✅ 已覆盖 | [`manage-equipment/SKILL.md` §场景 D](../skills/manage-equipment/SKILL.md) — `feishu_classmate_temi_rfid_scan_route` + 视觉位置确认 |
| 发现资产少了 → 飞书群上报 | ✅ 已覆盖 | [`manage-equipment/SKILL.md` §场景 D](../skills/manage-equipment/SKILL.md) — 差集后在广播群发摘要 |
| 后台:启用 RFID 扫描 + 定位 | ✅ 已覆盖 | 同上 |
| 后台:调飞书 API 更新【器材借还管理】 | ✅ 已覆盖 | 通过 lark 原生 `feishu_bitable_app_table_record` 操作 `Equipment` 表 |

### 借用登记

| PDF 条目 | 状态 | 依据 / Gap |
|---|---|---|
| 同学通过飞书/对话发起借用 | ✅ 已覆盖 | [`manage-equipment/SKILL.md` §场景 A](../skills/manage-equipment/SKILL.md) |
| 确认借阅后登记 | ✅ 已覆盖 | 场景 A 步骤 5 (update Equipment 行) |
| 归还后检查状态位置并更新 | ✅ 已覆盖 | [`manage-equipment/SKILL.md` §场景 B](../skills/manage-equipment/SKILL.md) |

**备注**: PDF 写的"多维表格"名字是"器材借还管理",我们代码里叫 `Equipment`(schema.ts),表名差异不影响功能,但讲给甲方看时口径要对齐。

---

## 模块 3:进度管理

对照 PDF 第 6 页。

### 甘特图生成

| PDF 条目 | 状态 | 依据 / Gap |
|---|---|---|
| 学生口述 / 丢文档 → Temi 总结 → 复述确认 | ✅ 已覆盖 | [`manage-gantt/SKILL.md` §场景 A 步骤 1–2](../skills/manage-gantt/SKILL.md) |
| 更新到飞书【甘特图】多维表格 | ✅ 已覆盖 | 步骤 3b `batch_create` Gantt 表 |
| 学生可继续口述修改或在飞书中修改 | 🟡 部分 | 后者(在飞书直接改)天然支持;前者"口述修改"没有专门的 update 分支,需要学生重新触发 manage-gantt skill |
| 后台:更新【可公开项目】/【保密项目】飞书文档 | ✅ 已覆盖 | 步骤 3c (追加到 `docs.publicProjects` / `docs.privateProjects`) |
| 后台:调"多维表格生成助手"生成甘特图表 | 🟡 部分 | 代码里是**直接**用 bitable record create 写行,而非调用飞书内置的多维表格生成助手。对用户来说效果等价,但实现路径不同 |

### 进度管理(每日节点提醒)

| PDF 条目 | 状态 | 依据 / Gap |
|---|---|---|
| 每日开机后检查当日是否是甘特图节点 | ✅ 已覆盖 | `services/gantt-scheduler.ts` cron `0 9 * * *` |
| 是则飞书发消息问进度 | ✅ 已覆盖 | [`manage-gantt/SKILL.md` §场景 B](../skills/manage-gantt/SKILL.md) |
| 读写【甘特图】【项目】多维表格 | ✅ 已覆盖 | 同 §场景 B 步骤 2 |

---

## 模块 4:自我监督

对照 PDF 第 7 页。

### 线上

| PDF 条目 | 状态 | 依据 / Gap |
|---|---|---|
| 学生飞书发指令 "监督我" | ✅ 已覆盖 | [`supervise-student/SKILL.md` §场景 A 启动](../skills/supervise-student/SKILL.md) 触发词齐全 |
| 每 10 分钟询问进度 | ✅ 已覆盖 | §场景 A 心跳(services/supervision-ticker.ts) |
| 制定【任务分解表】多维表格 | ❌ 未实现 | skill 里只写【日常记录】Doc,**没有任务分解表**。PDF 显式要求"调用飞书中的多维表格生成助手,为本次任务制定【任务分解表】表格"。当前 schema.ts 里也没有 TaskBreakdown 表 |
| 学生可协作修改表格 | ❌ 未实现 | 依赖上一条 |

### 线下

| PDF 条目 | 状态 | 依据 / Gap |
|---|---|---|
| 现场口述指令 | ✅ 已覆盖 | 与线上共用触发词 |
| 小目标 10 分钟询问 | ✅ 已覆盖 | 与线上共用心跳 |
| 摄像头检测是否专注 | ✅ 已覆盖 | [`supervise-student/SKILL.md` §场景 B](../skills/supervise-student/SKILL.md) — `feishu_classmate_temi_monitor_focus` |
| 连续摸鱼 → 语言 / 动作柔性干预 | ✅ 已覆盖 | §场景 B 步骤 3 — `temi_gesture` + `temi_speak` |
| 【任务分解表】+ 定时开摄像头 | 🟡 部分 | 摄像头 ✅;任务分解表 ❌(同上) |

---

## 模块 5:闲时行动

对照 PDF 第 8 页。

### 进行自己的研究课题

| PDF 条目 | 状态 | 依据 / Gap |
|---|---|---|
| 收集学生课题关键词,上网找相关研究 | ✅ 已覆盖 | [`idle-research/SKILL.md` §1–2](../skills/idle-research/SKILL.md) — 扫 Projects.keywords + `research_search_works` |
| 自行研究后输出研究报告(主题/相关工作/启发) | ✅ 已覆盖 | §3 LLM 综合 + §4 写 Research 表 |
| 生成到飞书【研究报告】区 | ✅ 已覆盖 | §5 `feishu_update_doc` 写 `docs.researchReports` |
| 综合分析各项目联系,输出高质量课题 | 🟡 部分 | 当前策略是"频次排序 + 去重";PDF 意图是"综合分析各项目**联系**",更偏向交叉分析。当前实现比较浅 |

### 闲聊

| PDF 条目 | 状态 | 依据 / Gap |
|---|---|---|
| 学生状态(专注/探索/卡顿)+ 历史互动判断是否需要帮助 | ✅ 已覆盖 | [`initiate-conversation/SKILL.md` §触发条件](../skills/initiate-conversation/SKILL.md) |
| 视觉识别学生状态 | 🟡 部分 | 代码里提到"Temi 视觉模块检测到工位有人";**但 PDF 说的"专注/探索/卡顿" 三态** 在 supervise-student 里有类似逻辑,chat skill 里只用了"有人/没人"的二值信号 |
| 聊天内容可能是今天机器人记录的事 / 研究成果 / 他人进度 | ✅ 已覆盖 | §话题选择 4 类(a-d)覆盖了这些来源 |
| 从【项目】/【研究报告】/【日常记录】文档找话题 | ✅ 已覆盖 | §话题选择 Projects / Research / DailyRecord 三张表 |

---

## 模块 6:自我进化(PDF 标记"待补充")

| PDF 条目 | 状态 | 依据 / Gap |
|---|---|---|
| 自我进化(待补充) | 🟡 部分 | **Phase 1 已实现** — [`evolve-telemetry/SKILL.md`](../skills/evolve-telemetry/SKILL.md) 本次 PR 新增;`ToolTrace` bitable 表 + `index.ts` 钩子自动记录每次 `feishu_classmate_*` 工具调用。**Phase 2 自动改写 SKILL.md / 建议新工具 — 未实现**(只在 evolve-telemetry §场景 D 给出启发式建议) |

---

## 模块 7:飞书工作空间(第 9 页架构图)

对照 PDF 知识库分区。

| PDF 条目 | 状态 | 依据 / Gap |
|---|---|---|
| 【可公开项目】文档 | ✅ 已覆盖 | `docs.publicProjects`(config.ts) |
| 【保密项目】文档 | ✅ 已覆盖 | `docs.privateProjects` |
| 【学生列表】文档 | ❌ 未实现 | config.ts `docs` 里没有 `studentList` 字段,也没有对应 skill 维护这张表 |
| 【日常记录(短期记忆)】文档 | ✅ 已覆盖 | `docs.dailyRecord` |
| 【日常记录(长期记忆)】文档 | ❌ 未实现 | 短期/长期**两套**未区分,只有一个 `docs.dailyRecord`。PDF 明示两份 |
| 【研究报告-A】【研究报告-B】… 多个独立的自我课题研究区 | 🟡 部分 | 当前只有一个 `docs.researchReports`。PDF 意图是**每个自主课题一份独立 Doc** |
| 【甘特图】多维表格 | ✅ 已覆盖 | `GANTT_TABLE`(schema.ts) |
| 【器材借还管理】多维表格 | ✅ 已覆盖 | `EQUIPMENT_TABLE` (名字叫 Equipment) |
| 工作群聊(老师 + 学生 A-D + 飞书同学) | 🟡 部分 | `labInfo.broadcastChatId` 存在;PDF 图里是"工作群聊"一个群,代码里统一用 broadcast chat id 也够 |

---

## 跨模块项目亮点(PDF 第 1 页 slogan)

| 亮点 | 状态 | 依据 / Gap |
|---|---|---|
| 实体机器人 Temi | ✅ 已覆盖 | `src/tools/temi/*` + sidecar + mock 模式 |
| 飞书知识库管理 | ✅ 已覆盖 | 6 张 bitable 表 + 多个 Doc 引用 |
| 自我进化 | 🟡 Phase 1 已交 | 见本 PR。Phase 2 未做 |
| 数据可视化 | ❌ 未实现 | PDF 第 2 页明确提到"可视化数据反馈"作为 OpenClaw+MetaClaw 的闭环。当前无任何可视化 skill / command / dashboard |

---

## What's missing 清单(punch-list,按优先级排)

下面这些是 PDF 明写但**当前未实现或部分实现**的,按影响 demo 可信度的权重排:

1. **【任务分解表】多维表格(自我监督)** ❌
   - PDF 线上/线下都明说要生成这张表并支持协作改表
   - 需要:在 `schema.ts` 加 `TASK_BREAKDOWN_TABLE`(fields: task_id, session_id, student_open_id, goal, sub_goals[], progress, status, created_at),在 `supervise-student/SKILL.md` 启动步骤里加建表 + LLM 拆 sub_goals

2. **日常记录 短期/长期记忆 分离** ❌
   - PDF 第 9 页图里明确两份
   - 需要:`config.ts docs` 增加 `dailyRecordLongTerm`,定一个"短期→长期"的沉淀策略(例如周度 digest 写入长期,同时短期只存 7 天)

3. **【学生列表】文档** ❌
   - 当前完全没有。影响:导览、daily-standup 枚举成员时只能反查 Projects.owner_open_id 去重,拿不到离校 / 休学的完整成员画像
   - 需要:`config.ts docs.studentList` + 一个 maintain-students skill(或纳入 admin 手工维护)

4. **数据可视化** ❌
   - PDF 顶部"项目亮点"之一,但实现里完全缺失
   - 需要:一个 `weekly-digest` 或 `data-viz` skill 生成图表(可以是 markdown 表 + 飞书 Sheet 图表,或导出 ECharts HTML)。注意 `WEEKLY_DIGESTS_TABLE` 已存在 schema 里,但还没有 skill 调它

5. **自我进化 Phase 2 — 自动改写 / 工具建议** 🟡
   - Phase 1 telemetry 已落地,但 SKILL 只教了"查询",没有自动化 close loop
   - 下一步:定时扫 `ToolTrace`,生成"建议补丁" PR

6. **每个自主课题一份独立研究报告 Doc** 🟡
   - 当前只有一个 `docs.researchReports` 全追加;PDF 架构图 每课题一份
   - 需要:idle-research 在写文档时用 `feishu_create_doc` 新建,把 doc_token 写回 Research 表

7. **导览阶段 3 的动作+表情** 🟡
   - 讲解词有,`temi_gesture` / `temi_expression` 这类动作工具在 tour skill 里没被调用
   - 需要:在 `conduct-lab-tour/SKILL.md §阶段 3` 加 gesture 触发逻辑,或者在 area.narration 里预埋 `<gesture:nod/>` 标记让 temi_speak 解析

8. **学生"口述修改"甘特图分支** 🟡
   - PDF 写"学生可继续口述修改",当前需要学生重新走一遍建项目流程
   - 需要:在 `manage-gantt` 加 update 场景(现在只有 progress 回填,没有 milestone 改日期/改名的分支)

9. **"多维表格生成助手"** 🟡
   - PDF 多处写要"调飞书多维表格生成助手",当前是用 bitable record API 直写。效果等价但展示上不如调助手直观
   - 需要:调研飞书是否开放该助手 API;若无,标注"技术等价实现"给演示用

10. **闲聊的三态视觉识别(专注/探索/卡顿)** 🟡
    - 当前只二值"在/不在"
    - 需要:把 `temi_monitor_focus` 的专注度分数映射到三态,暴露给 initiate-conversation

---

## 总计

- **已完整覆盖 (✅)**: 25 条
- **部分覆盖 (🟡)**: 11 条
- **未实现 (❌)**: 4 条

主要 demo 风险项集中在**自我监督的任务分解表**、**数据可视化**、**日常记录双记忆**三块。其余 🟡 多为实现深度问题,不影响功能跑通。
