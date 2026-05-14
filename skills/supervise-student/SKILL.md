---
name: supervise-student
description: |
  学生主动请求监督时使用,按间隔定时询问进度、检测专注度、柔性干预。
  支持线上(纯飞书)与线下(飞书 + Temi 视觉)两种模式。

  **触发词**: "监督我"、"supervise me"、"帮我盯一下"、"我要专心 N 小时"、
  "我要把 XX 跑通"。
---

# 自我监督 Skill

## 前置:拿数据布局

```
feishu_classmate_data_layout()
  → { app_token, docs: { dailyLogs }, labInfo: {...} }
```

不写 bitable 表;所有 session 记录走 `docs.dailyLogs`。
线下模式依赖 Temi,mock 模式下自动降级为线上。

## 场景 A:线上模式(纯软件)

示例: `飞书同学,我今天要把 RLHF 跑通,监督我 4 小时`

### 启动

1. `feishu_classmate_supervision_start({ student_open_id, goal, duration_hours: 4 })`
   → 拿到 `session_id`
2. 回复: "好的,接下来 4 小时我每 10 分钟问你一次进度。说'暂停'可以停。加油 💪"

### 心跳(每 10 分钟,由 services/supervision-ticker 或 agent 自调度)

1. DM 学生: "10 分钟了,现在状态?有卡点吗?"
2. 收到回复 → LLM 判定三态: `进行中` / `卡住` / `已完成`
3. 卡住 → 主动给建议:搜 GitHub issue、推 arxiv 相关论文、提议休息
4. 已完成 → 结束 session,进入"总结"

### 结束

1. 汇总所有 `progress_notes`
2. 写入 [日常记录 Doc](../idle-research/SKILL.md)(`docs.dailyLogs`)格式:
   ```
   ## {日期} · {学生 open_id}
   Goal: {goal}
   Duration: 4h
   Notes:
     - 10:10 开始 xxx
     - 10:20 卡在 yyy,建议看了 https://...
   Result: 已完成 / 未完成
   ```
3. DM 学生总结 + 鼓励

## 场景 B:线下模式(需要 Temi)

同 A,但额外:

1. 学生坐在工位 → `feishu_classmate_temi_monitor_focus({ student_open_id, duration_s: 600 })`
2. 摄像头每 10 秒采样专注度分数(0-1)
3. 连续 3 次 < 0.4(或 2 分钟内多次低分):
   - 先观察 60 秒
   - 仍低 → `feishu_classmate_temi_gesture({ type: "encourage" })` +
     `feishu_classmate_temi_speak({ text: "要不要起来活动一下?" })`
4. 学生说"停"/"别吵" → 立即停止干预,只继续记录
5. 专注度下降趋势 → 推送一篇高相关 arxiv 论文

## 边界与安全约束

- 必须得到学生**显式同意**才能启用摄像头监测(opt-in)
- 视频帧不落盘,只保留每秒一个专注度分数(0-1)
- `maxDurationHours` 限制 8 小时
- 学生发 "停止监督" / "结束" / "不用了" → 立即 `endSupervisionSession`
- 学生在半夜 00:00 之后启动 → 追加提醒 "建议先休息哦"

## 失败降级

- 学生连续 2 个心跳未回 → 温和提醒一次,再不回视为已结束
- Temi 离线(线下模式) → 自动降级为线上模式,通知学生
- `feishu_classmate_supervision_start` 失败 → 告诉学生"监督服务未就绪",
  建议手动用番茄钟
- `docs.dailyLogs` 未配 → 跳过归档,只 DM 总结

## 示例对话

```
学生: 监督我 2 小时把 PPO baseline 跑通
Bot:  好,每 10 分钟问一次进度。加油 💪
...(10 分钟后)
Bot:  10 分钟了,状态?
学生: 正在调 lr,loss 还在震荡
Bot:  收到。如果半小时还没稳,可以试试 warmup + linear decay。继续。
...(2 小时后)
Bot:  时间到 ✅ 2h 内完成 3 次调参,最终 reward 8200。纪要已归档到日常记录。
```
