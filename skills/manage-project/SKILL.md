---
name: manage-project
description: 项目及进度管理全流程支持，包括项目信息录入、甘特图自动更新、逾期智能检查、高优先级项目高颗粒度跟踪、智能帮扶提醒。所有文档、甘特图、项目表格均存储在飞书【Lab知识库】公共协作区。使用场景：创建新项目、更新项目进度、查询项目甘特图、查看项目进度、设置项目提醒、生成项目周报。
---

# 项目管理技能

## 场景导航
根据用户需求读取对应参考文档：
- **创建项目** → 读取 [project-creation.md](references/project-creation.md)
- **更新/查询进度** → 读取 [progress-check.md](references/progress-check.md)
- **生成周报** → 读取 [weekly-report.md](references/weekly-report.md)
- **项目卡点帮扶** → 读取 [intelligent-help.md](references/intelligent-help.md)
- **飞书API集成** → 读取 [FEISHU_INTEGRATION_GUIDE.md](references/FEISHU_INTEGRATION_GUIDE.md)

## 通用规则
### 字段规范
- 项目优先级：`普通`、`高优先级（任务重时间紧）`
- 节点状态：`未开始`、`进行中`、`已完成`、`逾期`
- 跟踪颗粒度：`3天`、`1天`、`2小时`

### 错误处理
- 公共协作区ID不存在：提示用户先配置
- 甘特表查询失败：跳过对应项目记录错误日志
- 消息发送失败：记录到项目日志下次检查重试

### 高优先级项目判断
同时满足：任务密度 > 0.5（总任务数/总天数）且 剩余天数 < 7天 → 标记为高优先级项目，自动启动专项跟踪
