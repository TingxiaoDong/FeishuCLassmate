<div align="center">

# 飞书同学 · Feishu Classmate

<img src="assets/hero.png" alt="飞书同学 · 让协作更智能、更轻松" width="100%" />

<br/>

<img src="https://img.shields.io/badge/🦞_OpenClaw-2026.4.10%2B-ff5a2d?style=flat-square" />
<img src="https://img.shields.io/badge/飞书-Feishu%2FLark-00d6b9?style=flat-square" />
<img src="https://img.shields.io/badge/Node-22%2B-339933?style=flat-square&logo=node.js&logoColor=white" />
<img src="https://img.shields.io/badge/TypeScript-5.9-3178c6?style=flat-square&logo=typescript&logoColor=white" />
<img src="https://img.shields.io/badge/Python-3.10%2B-3776ab?style=flat-square&logo=python&logoColor=white" />
<img src="https://img.shields.io/badge/Skills-28-blueviolet?style=flat-square" />
<img src="https://img.shields.io/badge/Tables-20%2B-orange?style=flat-square" />
<img src="https://img.shields.io/badge/License-MIT-yellow?style=flat-square" />

### 实验室办公场景下的**智能伙伴** · Lab Assistant for the Robotics Lab

**OpenClaw**(大脑) + **Temi**(身体) + **飞书**(记忆) + **MetaClaw**(技能注入)

[✨ Features](#-features) · [🚀 Quick Start](#-quick-start) · [🛠️ Skills](#️-skills-catalog) · [🏗️ Architecture](#️-architecture) · [📊 Data](#-data-model)

</div>

---

## 🔭 Overview

**飞书同学** 是给机器人实验室量身定制的 AI 实验伙伴,驻扎在飞书里,每天帮你:

- 🎓 **带访客参观** 实验室,Temi 走位 + TTS 讲解 + 工位区联动介绍
- 📋 **管理项目进度**,学生口述 → 自动生成甘特图、每日节点 @ 提醒
- 🔬 **记录实验/训练**,RL runs · checkpoints · sim-to-real gap 全留痕
- 📚 **跟踪论文和投稿**,arXiv 自动抓元数据、submission 状态机
- 🛠️ **器材借还和巡查**,RFID + 摄像头
- 👥 **师生协作**,导师 `/dashboard` 一览全组、自然语言派任务、1:1 自动议程
- 🧠 **技能沉淀**,每次对话都是学习信号,MetaClaw 把 lab 习惯注入 agent

> 赛道:开放创新赛道。

---

## ✨ Features

| 类别 | 功能 |
|---|---|
| 👋 **导览** | 5 阶段:开场白 → 实验室介绍 → 特色区域 → 工位区 → 问答 |
| 📊 **进度管理** | 学生口述 → 甘特图生成;每日 09:00 节点 @ 提醒 |
| 🔧 **器材管理** | 借还登记 + RFID 每日巡查 |
| 🧘 **自我监督** | 线上 DM 定时问进度 + 线下摄像头检测专注 + 柔性干预 |
| 💭 **闲时行动** | 自主研究周报(arXiv)+ 闲聊话题生成 |
| 🧬 **自我进化** | 每次 tool 调用轨迹入库 + MetaClaw 技能注入 |
| 🤖 **机器人专属** | 训练 Run、Checkpoint、Sim-to-Real Gap 追踪 |
| 👨‍🏫 **导师视角** | Dashboard、自然语言派任务、1:1 自动议程 |
| 👥 **协作成长** | Reading Group 轮值、师兄答疑调度、Skill Tree |
| 📖 **知识沉淀** | Failure Museum、FAQ 搜索、Lab Meme 档案 |
| 📝 **会议流程** | 每日 Standup、组会议程、会议纪要自动化 |
| 📚 **学术管理** | Paper 库、实验记录、设备预约、投稿追踪、周报聚合 |
| 🆕 **新生入职** | 12 项 Onboarding Checklist 自动跟进 |

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│  飞书 / Lark  ·  群聊 / 私信 / 多维表格 / 文档 / Drive / Calendar      │
└───────────────────────────────┬──────────────────────────────────────┘
                                │ WebSocket 长连接
┌───────────────────────────────▼──────────────────────────────────────┐
│  @larksuite/openclaw-lark       ← 官方通道插件(零代码)               │
│    · 消息收发 / Card / OAuth / Bitable / Doc / Drive / Calendar 工具  │
└───────────────────────────────┬──────────────────────────────────────┘
                                │
┌───────────────────────────────▼──────────────────────────────────────┐
│  OpenClaw core  ·  agent 会话 / 工具调度 / skill 注入                  │
│    model endpoint → http://127.0.0.1:30000/v1  (MetaClaw)             │
└───────────────────────────────┬──────────────────────────────────────┘
                                │ OpenAI 兼容
┌───────────────────────────────▼──────────────────────────────────────┐
│  MetaClaw proxy  ·  skills 模式                                       │
│    · skill_manager → 每轮注入相关 SKILL.md                            │
│    · memory layer → 跨会话 facts / preferences / project history     │
│    · 会话结束自动 summarize 成新 skill                                │
└───────────────────────────────┬──────────────────────────────────────┘
                                │
                 ┌──────────────┴─────────────────┐
                 │                                │
┌────────────────▼────────────┐    ┌──────────────▼──────────────────┐
│ feishu-classmate 插件       │    │  真实 LLM                        │
│                             │    │  (Anthropic / OpenAI / …)        │
│  tools/    temi/ supervisor/│    └─────────────────────────────────┘
│            chat/ research/  │
│  services/ gantt-scheduler  │    ┌─────────────────────────────────┐
│            idle-loop        │◄──►│ temi-sidecar (Python FastAPI)   │
│            equipment-patrol │    │  /goto /speak /stop /rfid ...   │
│            supervision-tick │    └──────────────┬──────────────────┘
│  skills/   28 × SKILL.md    │                   │ WebSocket
└─────────────────────────────┘    ┌──────────────▼──────────────────┐
                                   │       Temi Robot                │
                                   └─────────────────────────────────┘
```

---

## 🚀 Quick Start

### 1. 环境要求

| 依赖 | 版本 | 说明 |
|---|---|---|
| Node.js | 22+ | OpenClaw 要求 |
| Python | 3.10+ | Temi sidecar |
| pnpm | 10+ | 包管理 |
| OpenClaw | ≥ 2026.4.10 | `npm i -g openclaw` |
| MetaClaw | 可选 | `pip install aiming-metaclaw`(skills 模式) |
| 飞书自建应用 | — | 权限清单见 [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) |

### 2. 安装 + 启动

```bash
# 克隆 + 装依赖
git clone https://github.com/BaiTianHaoNian/feishu-classmate.git
cd feishu-classmate
pnpm install

# 配飞书应用(在 open.feishu.cn 创建,需要 bitable:app / base:app:create / docx:document / im:* 等)
cp .env.example .env
# 编辑 .env,填 FEISHU_APP_ID / FEISHU_APP_SECRET / LLM_API_KEY

# 配 OpenClaw 本地 gateway + 飞书通道
node_modules/.bin/openclaw config set gateway.mode local
node_modules/.bin/openclaw config set channels.feishu.appId "$FEISHU_APP_ID"
node_modules/.bin/openclaw config set channels.feishu.appSecret "$FEISHU_APP_SECRET"
node_modules/.bin/openclaw config set channels.feishu.domain feishu
node_modules/.bin/openclaw config set channels.feishu.dmPolicy open
node_modules/.bin/openclaw config set channels.feishu.groupPolicy open

# 装插件(本地链接模式)
pnpm build
node_modules/.bin/openclaw plugins install --link --dangerously-force-unsafe-install .
node_modules/.bin/openclaw plugins install --link --dangerously-force-unsafe-install node_modules/@larksuite/openclaw-lark
node_modules/.bin/openclaw plugins enable openclaw-lark

# 起 gateway
nohup node_modules/.bin/openclaw gateway run --bind loopback --port 18789 --force \
  > /tmp/openclaw-gateway.log 2>&1 &

# 初始化多维表 schema
node_modules/.bin/openclaw classmate setup-bitable

# 验证
./scripts/smoke.sh
```

### 3. 在飞书测试

1. 飞书 app → 搜索你的 bot → 私信
2. 发:`帮我建个项目:RLHF 6 周分 3 阶段`
3. Bot 应回复结构化草稿 → 确认 → 自动写入 Projects + Gantt bitable

运维手册: **[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)** · 部署检查单 · 权限清单 · 凭证轮换 · 回滚。

---

## 🛠️ Skills Catalog

**28 个 Agentic Skill**。每个 skill 是一份 `SKILL.md`,OpenClaw 自动注入 agent system prompt,让 LLM 按流程调官方 `@larksuite/openclaw-lark` 工具。

### 🎓 教学 / 访客

| Skill | 作用 |
|---|---|
| [conduct-lab-tour](skills/conduct-lab-tour/SKILL.md) | 5 阶段导览(开场白 → 实验室 → 特色区 → 工位区 → 问答) |
| [lab-onboarding](skills/lab-onboarding/SKILL.md) | 新生 12 项入职 checklist 自动跟进 |

### 📊 项目 / 进度

| Skill | 作用 |
|---|---|
| [manage-gantt](skills/manage-gantt/SKILL.md) | 口述 → 甘特图;每日节点提醒 |
| [weekly-digest](skills/weekly-digest/SKILL.md) | 每周五自动生成 lab 周报 |
| [daily-standup](skills/daily-standup/SKILL.md) | 每日站会汇总 |

### 🔬 实验 / 训练

| Skill | 作用 |
|---|---|
| [training-run-tracker](skills/training-run-tracker/SKILL.md) | RL/ML 训练 Run 元数据 + W&B/TB 链接 |
| [robot-checkpoint](skills/robot-checkpoint/SKILL.md) | Policy checkpoint + A/B 对比 |
| [simulation-log](skills/simulation-log/SKILL.md) | Sim-to-Real gap + 可复现 seed 管理 |
| [log-experiment](skills/log-experiment/SKILL.md) | 通用实验记录 |

### 📚 文献 / 投稿

| Skill | 作用 |
|---|---|
| [manage-papers](skills/manage-papers/SKILL.md) | arXiv 自动抓 + 本地 Papers 库 |
| [submission-tracking](skills/submission-tracking/SKILL.md) | 投稿状态机(准备中 → 已投 → 审稿 → 接收/拒/修改) |
| [idle-research](skills/idle-research/SKILL.md) | 闲时自主研究周报 |

### 🔧 器材 / 资源

| Skill | 作用 |
|---|---|
| [manage-equipment](skills/manage-equipment/SKILL.md) | 借还登记 + RFID 每日巡查 |
| [reserve-equipment](skills/reserve-equipment/SKILL.md) | GPU / 3D 打印机 / 显微镜时段预约 |

### 👨‍🏫 导师 / 管理

| Skill | 作用 |
|---|---|
| [supervisor-dashboard](skills/supervisor-dashboard/SKILL.md) | `/dashboard` 一键看所有学生进度 |
| [supervisor-task-assign](skills/supervisor-task-assign/SKILL.md) | 自然语言派任务 + 自动 DM |
| [one-on-one-scheduler](skills/one-on-one-scheduler/SKILL.md) | 1:1 排期 + 自动生成议程 |
| [supervise-student](skills/supervise-student/SKILL.md) | 学生自我监督会话(线上 + 线下) |

### 📋 会议 / 协同

| Skill | 作用 |
|---|---|
| [meeting-agenda](skills/meeting-agenda/SKILL.md) | 组会议程前 24h 收集 |
| [meeting-minutes](skills/meeting-minutes/SKILL.md) | 纪要 → 行动项 → 自动进 Gantt |
| [reading-group](skills/reading-group/SKILL.md) | 每周 paper 轮值 + 讨论点生成 |

### 👥 人才 / 成长

| Skill | 作用 |
|---|---|
| [mentor-dispatch](skills/mentor-dispatch/SKILL.md) | 新生提问 → 自动匹配师兄师姐 |
| [skill-tree](skills/skill-tree/SKILL.md) | 技能标签库(ROS / MuJoCo / RL / SLAM 等) |
| [initiate-conversation](skills/initiate-conversation/SKILL.md) | Bot 主动闲聊(有边界 + 冷却) |

### 📖 知识 / 文化

| Skill | 作用 |
|---|---|
| [failure-archive](skills/failure-archive/SKILL.md) | "失败博物馆" — 实验教训归档,防重复踩坑 |
| [lab-faq-search](skills/lab-faq-search/SKILL.md) | 入门 FAQ 搜索(Docker / GPU / SSH 等) |
| [lab-meme](skills/lab-meme/SKILL.md) | 实验室段子 / inside jokes(带 consent 审核) |

### 🧬 技能沉淀

| Skill | 作用 |
|---|---|
| [evolve-telemetry](skills/evolve-telemetry/SKILL.md) | 查询 ToolTrace 轨迹,辅助 skill 迭代 |

---

## 🔧 Tool Catalog

### Classmate 自有 tool(处理 raw Bitable 搞不定的)

| 组 | Tool | 用途 |
|---|---|---|
| `data` | `feishu_classmate_data_layout` | 返回 app_token + table_ids + 字段 schema |
| `temi` | `navigate_to` / `speak` / `stop` / `detect_person` / `status` / `rfid_scan` / `monitor_focus` / `gesture` | Temi sidecar HTTP 控制 |
| `supervision` | `start` / `tick` / `summarize` | 有状态的监督会话(内存) |
| `chat` | `pick_topic` / `should_engage` | 闲聊触发冷却 |
| `research` | `search_works` | arXiv 搜索 |

### 官方 lark 插件 tool(数据操作主力,来自 `@larksuite/openclaw-lark`)

- `feishu_bitable_app*` · 多维表应用 / 表 / 记录 / 字段 / 视图
- `feishu_fetch_doc` / `create_doc` / `update_doc` / `doc_comments` / `doc_media`
- `feishu_drive_file` / `feishu_wiki_space*` / `feishu_sheet`
- `feishu_task*` / `feishu_calendar*`
- `feishu_search_doc_wiki` / `feishu_oauth` / `feishu_ask_user_question`

> **设计原则**:Bitable/Doc/Drive 读写**全部**走 lark 官方 tool。Classmate 只在 raw lark 搞不定的地方(硬件、状态、非 Feishu 服务)补位。Skill 层负责编排。

---

## 📊 Data Model

**20+ Bitable 表**,首次运行 `openclaw classmate setup-bitable` 自动创建:

| 域 | 表 |
|---|---|
| 项目 | `Projects` · `Gantt` · `Assignments` |
| 实验 | `Experiments` · `TrainingRuns` · `Checkpoints` · `SimRuns` |
| 文献 | `Papers` · `Submissions` |
| 器材 | `Equipment` · `Reservations` |
| 人员 | `SkillTree` |
| 会议 | `Standups` · `ReadingGroup` · `OneOnOnes` |
| 知识 | `FailureArchive` · `LabFAQ` · `MentorAnswers` · `LabMemes` |
| 报告 | `Research` · `WeeklyDigests` |
| 遥测 | `ToolTrace` |

PDF 对照审计见 **[docs/PDF_COMPLIANCE.md](docs/PDF_COMPLIANCE.md)**。

---

## 🔌 Plugin Stack

| 层 | 组件 | 作用 |
|---|---|---|
| 1 | **OpenClaw core** | Agent 调度、会话、工具注入 |
| 2 | **@larksuite/openclaw-lark** | 飞书通道 + 官方数据工具 |
| 3 | **MetaClaw**(可选) | 透明 LLM 代理 · skills 模式(技能注入 + 跨会话记忆) |
| 4 | **feishu-classmate**(本仓库) | 实验室业务 + 硬件控制 |
| 5 | **temi-sidecar**(Python FastAPI) | Temi 机器人 HTTP 网关,mock-capable |

---

## 🛠️ Development

```bash
pnpm typecheck   # 类型检查
pnpm build       # 编译
pnpm test        # Vitest
pnpm format      # Prettier
```

### 加新 skill

1. 新建 `skills/<name>/SKILL.md`,照 [manage-gantt/SKILL.md](skills/manage-gantt/SKILL.md) 模板
2. 重启 gateway,OpenClaw 自动扫到
3. 在 skill 里**只**用 `@larksuite/openclaw-lark` 的 raw tool + `feishu_classmate_data_layout`,不写新 zod tool

### 加新 tool(仅当 raw lark 搞不定时)

1. `src/tools/<group>/<name>.ts` 用 `registerZodTool(api, {...})`
2. `src/tools/index.ts` 加注册
3. `pnpm build && openclaw gateway restart`

### 目录结构

```
feishu-classmate/
├── index.ts                     # 插件入口
├── src/
│   ├── config.ts                # 配置读取 + env 回退
│   ├── bitable/
│   │   ├── schema.ts            # 20+ TableDef 声明
│   │   └── setup.ts             # 幂等建表 + sidecar 状态持久化
│   ├── tools/
│   │   ├── data-layout.ts       # 唯一的 bitable 相关 tool
│   │   ├── temi/                # 8 个 temi sidecar tool
│   │   ├── supervision/         # 3 个监督会话 tool
│   │   ├── chat/                # 闲聊冷却
│   │   └── research/search-works.ts  # arXiv
│   ├── services/                # 4 个 cron
│   └── util/
│       ├── register-tool.ts     # zod→TypeBox 适配器
│       └── feishu-api.ts        # @larksuiteoapi/node-sdk 包装
├── skills/                      # 28 × SKILL.md
├── temi-sidecar/                # Python FastAPI + mock
├── scripts/
│   ├── smoke.sh                 # 部署冒烟
│   ├── dev.sh                   # 开发启动
│   └── curl-examples.md         # sidecar 调试
├── docs/
│   ├── DEPLOYMENT.md
│   └── PDF_COMPLIANCE.md        # PDF 原规格对照审计
└── tests/                       # Vitest
```

---

## 🙏 Related Projects

- [aiming-lab/MetaClaw](https://github.com/aiming-lab/MetaClaw) — 透明 LLM 代理 · skills 模式 · memory layer
- [aiming-lab/ClawArena](https://github.com/aiming-lab/ClawArena) — Agent 评测 arena
- [openclaw/openclaw](https://github.com/openclaw/openclaw) — 个人 AI 助手 CLI
- [larksuite/openclaw-lark](https://github.com/larksuite/openclaw-lark) — 飞书通道插件

---

## 📚 Citation

```bibtex
@software{feishu_classmate_2026,
  title  = {Feishu Classmate: A Lab-Scenario AI Assistant on OpenClaw + MetaClaw},
  author = {Feishu Classmate Contributors},
  year   = {2026},
  url    = {https://github.com/BaiTianHaoNian/feishu-classmate},
  note   = {Built on @larksuite/openclaw-lark and aiming-lab/MetaClaw (skills mode)}
}
```

---

## 📄 License

MIT — 欢迎 fork / 改造 / 商用。

<div align="center">

*"Built for the robotics lab, by the robotics lab."*

⭐️ Star this repo if it helps your lab run smoother!

</div>
