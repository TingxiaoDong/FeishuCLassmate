---
name: "autonomous-research"
description: "自动读取飞书LAB知识库项目文档，自主确定研究课题，联网检索前沿案例和方向，生成研究报告辅助团队。Invoke when: 每周自动触发/用户说「启动自主研究」/项目有重大进展或卡点时"
---

# 自主研究技能

## 执行流程（按顺序执行）
1. 项目信息采集 → 读取 [project-collection.md](references/project-collection.md)
2. 研究课题确定 → 读取 [topic-selection.md](references/topic-selection.md)
3. 多维度信息检索 → 读取 [information-retrieval.md](references/information-retrieval.md)
4. 研究报告生成 → 读取 [report-generation.md](references/report-generation.md)
5. 结果推送应用 → 读取 [result-push.md](references/result-push.md)

## 通用规则
### 触发条件
- 自动触发：每周一09:00全量扫描 / 项目标记为高优先级 / 项目新增卡点
- 手动触发：用户要求启动研究、调研方向、查找参考案例

### 错误处理
- 【LAB知识库】访问失败 → 终止研究，记录日志下次重试
- 无匹配研究课题 → 终止执行，不发送通知
- 联网搜索失败 → 仅基于现有知识库内容生成报告
- 报告生成失败 → 跳过当前课题，尝试下一个候选课题

### 数据布局
调用 `feishu_classmate_data_layout()` 获取配置：
- 项目文档读取自【LAB知识库】公共协作区
- 研究报告存储到`research_reports`多维表和【研究报告】目录

