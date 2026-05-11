# 执行期 · 阶段与安全

## 与当次 Doc 的映射

| Doc 章节 | Temi 动作摘要 |
|----------|----------------|
| 开场 | `navigate_to` →「入口」(或与 lab 约定点位) → `speak` |
| 实验室概况 | `speak` |
| 特色实验区 | 遍历 `labInfo.specialAreas`:每处 `navigate_to(area.name)` → `speak(area.narration)`;Doc 有额外句则并入 speak |
| 工位区 | `navigate_to("工位区")` → `detect_person` → 若有公开项目则 bitable list Projects → `speak` |
| 人形机器人展区 | `navigate_to` 对应保存点位名称 → `speak` |
| 仿真与生活模拟区 | 同上 |
| 收尾与问答 | `navigate_to`「入口」或原地 → `speak` 邀请提问 |
| 唤醒 | 执行期**不朗读**;仅作准备期约定的触发句备案 |

无 Doc 时:按 [**fallback-generic-tour**](../../conduct-lab-tour/references/fallback-generic-tour.md) 五阶段执行。

## 工位区 bitable(公开项目)

- `feishu_bitable_app_table_record` `action=list`, table_id 来自 `data_layout.tables.projects`
- `filter` 示例:`AND(CurrentValue.[owner_open_id]=[{id:"<ou_xxx>"}],CurrentValue.[visibility]="可公开")`
- 仅将 **title** 用于口播,**不要**在飞书消息中暴露 `open_id` 原文

## 问答

- 知识来源:当次 Doc + publicProjects Doc + `labInfo`
- 结束语:用户说「谢谢/结束/bye」或轮次上限后 `speak` 告别

## 安全

- 不透露保密项目;`temi_stop` 见主 SKILL

## 事后(可选)

- 摘要写入 `plugin_docs.dailyRecord` / `dailyRecordShortTerm` 对应日常记录 Doc
