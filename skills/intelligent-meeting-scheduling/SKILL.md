---
name: intelligent-meeting-scheduling
description: 智能会议预约与会前提醒。使用场景：导师通过飞书发送会议需求后，自动读取参会人日程并安排共同空闲时间，创建会议并在临近会议时优先通过Temi线下寻人提醒，未找到则飞书私信提醒。
---

# 智能会议预约

## 使用流程（需求原文）
导师通过飞书向Agent发送会议基本信息，agent自动访问相关人员的日程，查看其共同空闲时间，进行会议日程的安排。临近会议时，Agent在实验室内寻找参会人员进行提醒，若没找到则通过飞书线上发消息提醒。

## 场景导航
- **会议排期** → 读取 [references/scheduling-and-reminder.md](references/scheduling-and-reminder.md)
- **Temi动作编排** → 优先使用 `feishu_classmate_temi_status` / `feishu_classmate_temi_navigate_to` / `feishu_classmate_temi_detect_person` / `feishu_classmate_temi_speak`

## 快速执行规则
1. 先补齐会议最小信息：主题、时长、发起人、参会人列表、期望日期范围、会议地点。
2. 参会人必须落到可调用日程接口的身份标识（优先 `open_id`）。
3. 使用飞书日程工具族（`feishu_calendar*`）查询各参会人可用时段，计算共同空闲窗口后给出候选时间。
4. 确认最终时间后，通过飞书日程工具创建会议并向参会人同步会议信息。
5. 会前提醒默认在会议开始前30分钟触发：先线下寻人，再飞书兜底。
6. 线下提醒按参会人逐个执行；同一参会人同一场会议仅提醒一次。

## 通用约束
- 语气保持正向、热心、帮扶导向，禁止催促式表达。
- 工具失败时要降级：`Temi失败/未识别` → 飞书私信；`日程接口受限` → 给出候选时间草案并请求人工确认。
- 任何写入前先校验时区（默认 Asia/Shanghai）与会议时长单位（分钟）。
