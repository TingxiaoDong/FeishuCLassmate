---
name: lab-tour-run
description: |
  访客到达现场后的「执行期」实验室导览:Temi 走位 + 播报 + 工位项目补充 + 问答。
  **前置**:已有当次讲解 Doc(由 skill `lab-tour-prepare` 生成),或使用通用内置剧本。
  **触发**: 「开始导览」「参观开始」「飞书同学 XX 到了」、用户提供 doc 链接/token。

  **不要用于**: 仅在飞书里写稿不发机器人 —— 用 `lab-tour-prepare`。
---

# 导览 · 执行期

## 最短路径

1. `feishu_classmate_data_layout()` → `plugin_docs`、`labInfo`。
2. `feishu_classmate_temi_status` → 若未连接且非 mock,改为**纯文字**在飞书输出各段文案。
3. 若有当次 Doc:`feishu_fetch_doc` 拉全文,按 [doc-format](../lab-tour-prepare/references/doc-format.md) 的 `##` 分段;无 Doc 则退回 [fallback-generic-tour](../conduct-lab-tour/references/fallback-generic-tour.md)。
4. 每段:**必要时** `temi_navigate_to` → `temi_speak`(读本段压缩稿,单段不宜过长)。
5. **工位区**段额外:读 `plugin_docs.publicProjects`,必要时 bitable 查公开项目,见 detail。
6. **收尾与问答**:`temi_speak` 邀请提问;随后在用户回复或语音通道内作答,**只听公开资料与当次 Doc**,拒答保密内容。
7. 全程「停/stop」→ `feishu_classmate_temi_stop({ immediate: true })`。

## 详细阶段与安全

见 [references/run-detail.md](./references/run-detail.md)。
